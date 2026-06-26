import json
from guardrails import Guard
from guardrails.validators import Validator, register_validator, PassResult, FailResult
try:
    from guardrails.hub import OnFailAction
except ImportError:
    from guardrails.validator_base import OnFailAction

@register_validator(name='custom/test-json3', data_type='string')
class TestJSON3(Validator):
    def validate(self, value, metadata):
        try:
            parsed = json.loads(value)
            formatted = json.dumps(parsed, indent=2)
            return FailResult(error_message='reformatted', fix_value=formatted)
        except Exception as e:
            fallback = json.dumps({'error': 'invalid JSON'})
            return FailResult(error_message=str(e), fix_value=fallback)

guard = Guard().use(TestJSON3(on_fail=OnFailAction.FIX))
test_input = '{"name": "Alice"}'
result = guard.validate(test_input)
print("passed=%s" % result.validation_passed)
print("output=%s" % str(result.validated_output)[:80])
