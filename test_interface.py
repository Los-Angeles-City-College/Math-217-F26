"""Run with the full application requirements installed."""
import importlib.util
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("streamlit") and importlib.util.find_spec("plotly"), "Install requirements.txt to run interface checks")
class InterfaceTests(unittest.TestCase):
    def test_all_modes_render(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        self.assertFalse(at.exception)
        for mode in ["Contribution amount", "Return rate", "Starting amount", "Investment length", "Ending balance"]:
            at.selectbox[0].select(mode).run(timeout=30)
            self.assertFalse(at.exception, mode)
            self.assertFalse(at.error, mode)
            self.assertEqual(len(at.metric), 4)

    def test_negative_return_and_zero_inputs(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        next(w for w in at.number_input if w.label == "Annual return (%)").set_value(-10.0)
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        for label in ["Starting amount ($)", "Additional contribution ($)"]:
            next(w for w in at.number_input if w.label == label).set_value(0.0)
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[0].value, "$0.00")
