import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import transform,validate_config
from calendars import boc_events
class CollectionTests(unittest.TestCase):
 def test_annual_inflation_uses_same_month_not_row_position(self):
  p=[{'date':'2025-01','value':100},{'date':'2025-03','value':200},{'date':'2026-01','value':110},{'date':'2026-02','value':220}]
  out=transform(p,'yoy');self.assertAlmostEqual(out[2]['value'],10);self.assertIsNone(out[3]['value'])
 def test_fx_direction_and_missing(self):
  self.assertEqual(transform([{'date':'2026-01-01','value':1.25}],'reciprocal')[0]['value'],.8)
  self.assertIsNone(transform([{'date':'2026-01-02','value':None}],'reciprocal')[0]['value'])
 def test_calendar_reads_explicit_year_and_dates(self):
  page='<table><caption>Schedule for 2027</caption><tr><td>January&nbsp;27</td><td>Interest rate announcement</td></tr></table>'
  self.assertEqual(boc_events(page,'https://www.bankofcanada.ca/')[0]['date'],'2027-01-27')
  with self.assertRaises(ValueError):boc_events('<p>No schedule</p>','https://example.org')
 def test_new_series_does_not_require_six(self):
  validate_config({'periods':72,'series':[{'id':'new-source','provider':'valet','transform':'level'}]})
