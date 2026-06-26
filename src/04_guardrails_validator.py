"""
Bước 4 — Guardrails AI Validators
====================================
NHIỆM VỤ:
  1. Xây dựng PIIDetector: phát hiện & redact email, số điện thoại, SSN, số thẻ tín dụng
  2. Xây dựng JSONFormatter: tự động sửa JSON lỗi
  3. Bọc mỗi validator trong Guard và test với các mẫu đầu vào
  4. Chạy demo với ít nhất 5 trường hợp PII và 4 trường hợp JSON

DELIVERABLE: Tất cả test cases pass (PII bị redact, JSON được sửa thành công)

CÁC KHÁI NIỆM CHÍNH:
  - @register_validator     — khai báo custom validator class
  - Validator.validate()    — implement logic kiểm tra + sửa
  - OnFailAction.FIX        — thay thế output thay vì raise error
  - Guard().use(validator)  — gắn validator instance vào guard
  - guard.validate(text)    — ValidationOutcome
      .validation_passed    — bool
      .validated_output     — output đã được xử lý

NOTE: on_fail phải truyền vào CONSTRUCTOR của VALIDATOR, KHÔNG phải Guard.use()
    SAI  : Guard().use(PIIDetector, on_fail=OnFailAction.FIX)
    DUNG : Guard().use(PIIDetector(on_fail=OnFailAction.FIX))

NOTE2: Dung FailResult(fix_value=...) voi on_fail=FIX de override output.
       PassResult(value_override=...) khong hoat dong trong guardrails v0.6+.
"""

import re
import json

from guardrails import Guard
from guardrails.validators import Validator, register_validator, PassResult, FailResult

try:
    from guardrails.hub import OnFailAction
except ImportError:
    from guardrails.validator_base import OnFailAction


# ── 1. PII Detector Validator ──────────────────────────────────────────────
@register_validator(name="custom/pii-detector", data_type="string")
class PIIDetector(Validator):
    """
    Phat hien va redact Personally Identifiable Information (PII).

    Cac pattern duoc phat hien:
      EMAIL       : xxx@xxx.xxx
      PHONE       : (123) 456-7890 hoac 123-456-7890
      SSN         : 123-45-6789
      CREDIT_CARD : 1234 5678 9012 3456 (hoac dau gach noi)
    """

    # Regex patterns for PII detection
    PII_PATTERNS = {
        "EMAIL":       r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE":       r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}",
        "SSN":         r"\b\d{3}-\d{2}-\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    }

    def validate(self, value: str, metadata: dict):
        """
        Tim PII trong value; neu phat hien, redact va tra ve FailResult(fix_value=redacted).
        on_fail=FIX se dung fix_value lam output cuoi cung.

        Buoc:
          1. Copy value -> redacted_text
          2. Voi moi loai PII va pattern tuong ung:
             - Tim tat ca matches bang re.findall(pattern, value)
             - Thay the tung match bang "[PII_TYPE_REDACTED]" trong redacted_text
             - Ghi lai (pii_type, match) vao found_pii
          3. Neu found_pii khong rong -> FailResult(fix_value=redacted_text)
          4. Neu khong tim thay PII -> PassResult()
        """
        redacted_text = value
        found_pii     = []

        # Loop through PII patterns
        for pii_type, pattern in self.PII_PATTERNS.items():
            # Find all matches
            matches = re.findall(pattern, value)

            for match in matches:
                # Replace match with "[PII_TYPE_REDACTED]" in redacted_text
                redacted_text = redacted_text.replace(match, f"[{pii_type}_REDACTED]")
                found_pii.append((pii_type, match))

        if found_pii:
            pii_types = [p[0] for p in found_pii]
            print(f"  WARNING: Detected and redacted {len(found_pii)} PII item(s): {pii_types}")
            # Use FailResult with fix_value so on_fail=FIX replaces output with redacted text
            return FailResult(
                error_message=f"PII detected: {pii_types}",
                fix_value=redacted_text
            )

        # No PII found - pass through
        return PassResult()


# ── 2. JSON Formatter Validator ────────────────────────────────────────────
@register_validator(name="custom/json-formatter", data_type="string")
class JSONFormatter(Validator):
    """
    Validate va tu dong sua JSON loi.

    Cac loi co the sua tu dong:
      - Strip markdown code fences (``` hoac ```json)
      - Thay single quotes -> double quotes
      - Xoa trailing commas truoc } hoac ]
      - Re-serialize voi json.dumps de dinh dang chuan
    """

    @staticmethod
    def _repair(text: str) -> str:
        """
        Co gang sua chuoi JSON loi.

        Buoc:
          1. Strip whitespace dau/cuoi
          2. Xoa markdown fences bang re.sub
          3. Thay single quotes -> double quotes
          4. Xoa trailing commas truoc } hoac ]
          5. Tra ve chuoi da sua (chua re-serialize)
        """
        text = text.strip()

        # Xoa markdown fences
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$',          '', text)
        text = text.strip()

        # Thay single quotes -> double quotes
        text = text.replace("'", '"')

        # Xoa trailing commas
        text = re.sub(r',\s*([}\]])', r'\1', text)

        return text

    def validate(self, value: str, metadata: dict):
        """
        Thu parse value thanh JSON.
        Neu that bai, goi _repair() roi thu lai.

        Tra ve FailResult(fix_value=formatted_json) de Guardrails dung lam output.
        Tra ve FailResult(fix_value=fallback) neu JSON khong the sua duoc.
        """
        # Thu parse JSON truc tiep
        try:
            parsed = json.loads(value)
            formatted = json.dumps(parsed, indent=2)
            # Always return the formatted version via FailResult+fix_value
            return FailResult(
                error_message="JSON reformatted",
                fix_value=formatted
            )
        except json.JSONDecodeError:
            pass

        # Thu sua JSON roi parse lai
        try:
            repaired_text = self._repair(value)
            parsed        = json.loads(repaired_text)
            formatted     = json.dumps(parsed, indent=2)
            print("  JSON repaired successfully")
            return FailResult(
                error_message="JSON repaired and reformatted",
                fix_value=formatted
            )
        except json.JSONDecodeError as e:
            # Cannot fix - return a safe fallback
            fallback = json.dumps({"error": "invalid JSON", "original": value[:50]})
            return FailResult(
                error_message=f"JSON could not be repaired: {e}",
                fix_value=fallback
            )


# ── 3. Demo: PII Guard ─────────────────────────────────────────────────────
def demo_pii_guard():
    print("\n" + "=" * 55)
    print("  Demo PII Detector")
    print("=" * 55)

    # Create Guard with PIIDetector - on_fail must go to the CONSTRUCTOR
    guard = Guard().use(PIIDetector(on_fail=OnFailAction.FIX))

    test_cases = [
        ("Email",        "Contact John at john.doe@example.com for details."),
        ("Phone",        "Call our support line at (555) 867-5309."),
        ("SSN",          "Patient SSN is 123-45-6789 on file."),
        ("Credit Card",  "Payment made with card 4532 1234 5678 9010."),
        ("Multi-PII",    "Email: alice@example.com, Phone: 555-123-4567"),
        ("Clean",        "No sensitive information in this text."),
    ]

    for label, text in test_cases:
        result = guard.validate(text)

        print(f"\n[{label}]")
        print(f"  Input:  {text}")
        print(f"  Output: {result.validated_output}")


# ── 4. Demo: JSON Guard ────────────────────────────────────────────────────
def demo_json_guard():
    print("\n" + "=" * 55)
    print("  Demo JSON Formatter")
    print("=" * 55)

    # Create Guard with JSONFormatter - on_fail must go to the CONSTRUCTOR
    guard = Guard().use(JSONFormatter(on_fail=OnFailAction.FIX))

    test_cases = [
        ("Valid JSON",       '{"name": "Alice", "age": 30}'),
        ("Markdown fences",  '```json\n{"name": "Bob"}\n```'),
        ("Single quotes",    "{'name': 'Charlie', 'score': 95}"),
        ("Trailing comma",   '{"key": "value",}'),
        ("Truly invalid",    "This is not JSON at all: ??? {]"),
    ]

    for label, text in test_cases:
        result = guard.validate(text)

        status = "PASS" if result.validation_passed else "FAIL"
        print(f"\n[{label}] {status}")
        print(f"  Input:  {text[:60]}")
        print(f"  Output: {str(result.validated_output)[:80]}")


# ── 5. Main ────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Buoc 4: Guardrails AI Validators")
    print("=" * 55)

    demo_pii_guard()
    demo_json_guard()

    print("\nBuoc 4 hoan thanh!")


if __name__ == "__main__":
    main()
