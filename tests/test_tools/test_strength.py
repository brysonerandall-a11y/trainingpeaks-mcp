"""Tests for the structured-strength prescription builder."""

from tp_mcp.tools.strength import _build_prescription


class TestBuildPrescriptionOwnerId:
    """Regression guard for the ownerId fallback.

    TrainingPeaks rejects the whole workout ("Invalid workout") when an
    exercise's ownerId is empty. The library lookup returns entries with no
    usable ownerId, so the builder must fall back to the default. `dict.get`
    with a default only triggers on a *missing* key, not a present-but-empty
    one, so a present None/"" silently shipped an empty ownerId.
    """

    _DEFAULT_OWNER = 2000301

    def test_missing_owner_id_uses_default(self):
        presc = _build_prescription({"exerciseId": 131, "title": "Back Squat"}, [{"reps": 5}])
        assert presc["exercise"]["ownerId"] == self._DEFAULT_OWNER

    def test_none_owner_id_uses_default(self):
        # The actual production case: key present, value None.
        presc = _build_prescription(
            {"exerciseId": 131, "title": "Back Squat", "ownerId": None}, [{"reps": 5}]
        )
        assert presc["exercise"]["ownerId"] == self._DEFAULT_OWNER

    def test_empty_string_owner_id_uses_default(self):
        presc = _build_prescription(
            {"exerciseId": 131, "title": "Back Squat", "ownerId": ""}, [{"reps": 5}]
        )
        assert presc["exercise"]["ownerId"] == self._DEFAULT_OWNER

    def test_real_owner_id_is_preserved(self):
        presc = _build_prescription(
            {"exerciseId": 131, "title": "Back Squat", "ownerId": 12345}, [{"reps": 5}]
        )
        assert presc["exercise"]["ownerId"] == 12345
