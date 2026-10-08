import math
import unittest
from dataclasses import replace
from app import Plan, future_value, schedule, solve, MODES


class CalculatorTests(unittest.TestCase):
    def test_reference_example(self):
        self.assertAlmostEqual(future_value(Plan()), 198290.40, delta=0.005)

    def test_zero_return(self):
        self.assertAlmostEqual(future_value(Plan(rate=0)), 140000)
        self.assertAlmostEqual(future_value(Plan(rate=0, frequency="Annually")), 30000)

    def test_closed_form_end_monthly(self):
        p = Plan(compounding="Monthly", timing="End")
        q = 1.005
        expected = 20000 * q**120 + 1000 * (q**120 - 1) / (q - 1)
        self.assertAlmostEqual(future_value(p), expected, places=6)
        self.assertAlmostEqual(schedule(p)[-1]["Ending balance"], expected, places=6)

    def test_beginning_earns_one_more_month(self):
        p = Plan(starting=0, months=12, compounding="Monthly", timing="End")
        self.assertAlmostEqual(future_value(replace(p, timing="Beginning")), future_value(p) * 1.005, places=7)

    def test_annual_deposit_boundary(self):
        p = Plan(starting=0, rate=0, months=11, frequency="Annually", timing="End")
        self.assertEqual(future_value(p), 0)
        self.assertEqual(future_value(replace(p, months=12)), 1000)
        self.assertEqual(future_value(replace(p, timing="Beginning")), 1000)
        self.assertEqual(future_value(replace(p, timing="Beginning", months=13)), 2000)

    def test_inverse_solvers(self):
        for mode in ("Contribution amount", "Starting amount", "Return rate"):
            p, _ = solve(Plan(), mode, 250000)
            self.assertAlmostEqual(future_value(p), 250000, places=5)

    def test_length_solver_first_crossing(self):
        p, _ = solve(Plan(starting=0, contribution=100, rate=0), "Investment length", 1250)
        self.assertEqual(p.months, 13)

    def test_nonmonotone_length(self):
        p, _ = solve(Plan(starting=0, contribution=1000, rate=-50, frequency="Annually", timing="Beginning"), "Investment length", 900)
        self.assertEqual(p.months, 1)

    def test_unreachable_goal(self):
        with self.assertRaises(ValueError):
            solve(Plan(starting=100, contribution=0, rate=-10), "Investment length", 200)

    def test_already_reached(self):
        p, _ = solve(Plan(), "Investment length", 10000)
        self.assertEqual(p.months, 0)
        p, _ = solve(Plan(), "Contribution amount", 10000)
        self.assertEqual(p.contribution, 0)

    def test_zero_horizon(self):
        self.assertEqual(future_value(Plan(months=0)), 20000)
        with self.assertRaises(ValueError):
            solve(Plan(months=0), "Contribution amount", 20001)

    def test_rate_unidentifiable(self):
        with self.assertRaises(ValueError):
            solve(Plan(starting=0, months=1, timing="End"), "Return rate", 1000)

    def test_negative_return_and_inflation(self):
        p = Plan(starting=1000, contribution=0, months=12, rate=-10, inflation=5)
        self.assertAlmostEqual(future_value(p), 900)
        self.assertAlmostEqual(schedule(p)[-1]["Balance in today's dollars"], 900 / 1.05)

    def test_schedule_agrees_all_conventions(self):
        for compound in ("Annually", "Monthly", "Daily (365/year)", "Continuously"):
            for timing in ("Beginning", "End"):
                for frequency in ("Monthly", "Annually"):
                    p = Plan(compounding=compound, timing=timing, frequency=frequency, months=25, rate=-5)
                    rows = schedule(p)
                    self.assertAlmostEqual(rows[-1]["Ending balance"], future_value(p), places=6)
                    self.assertAlmostEqual(sum(r["Deposit"] + r["Interest"] for r in rows), rows[-1]["Ending balance"], places=6)

    def test_continuous(self):
        p = Plan(starting=1000, contribution=0, months=12, rate=10, compounding="Continuously")
        self.assertAlmostEqual(future_value(p), 1000 * math.exp(0.1))

    def test_continuous_solver_large_search_bounds(self):
        p = Plan(starting=1000, contribution=0, months=1200, compounding="Continuously")
        solved, _ = solve(p, "Return rate", 1000000)
        self.assertAlmostEqual(solved.rate, math.log(1000), places=7)
        solved, _ = solve(replace(p, rate=1000), "Investment length", 2000)
        self.assertEqual(solved.months, 1)

    def test_validation(self):
        for p in (Plan(starting=-1), Plan(rate=float("nan")), Plan(months=1201)):
            with self.assertRaises(ValueError):
                future_value(p)


if __name__ == "__main__":
    unittest.main()
