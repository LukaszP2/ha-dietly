"""Unit tests for identity namespace generation."""

from __future__ import annotations

import unittest

from custom_components.dietly.identity import entity_namespace


class TestIdentity(unittest.TestCase):
    """Test identity hashing functions."""

    def test_entity_namespace_stability(self) -> None:
        """Verify that identical inputs produce stable 20-character hex output."""
        id1 = entity_namespace("12345", "")
        id2 = entity_namespace("12345", "")
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 20)

    def test_entity_namespace_different(self) -> None:
        """Verify that different accounts produce different namespaces."""
        id1 = entity_namespace("12345", "")
        id2 = entity_namespace("67890", "")
        self.assertNotEqual(id1, id2)


if __name__ == "__main__":
    unittest.main()
