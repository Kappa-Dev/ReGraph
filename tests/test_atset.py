"""Testing of attribute sets module `atset.py`."""
from regraph.atset import to_atset


class TestAtSet:
    """Main class for AtSet testing."""

    def test_simple_attr(self):
        """Test the behaviour of to_atset."""
        a = {"a": {1}}
        print()
        print(a)
        print(to_atset(a["a"]))
