import csv
import io
import unittest
from transaction_export import build_transaction_csv,ExportStopped,_cell


def row(**kwargs):
 r={'amount':'-12.40','currency':'EUR','currency_known':True,'status':'booked','date':'2026-11-19',
    'date_source':'transaction_date','date_inferred':False,'description':'Synthetic text'}
 r.update(kwargs);return r

def decoded(result):return list(csv.reader(io.StringIO(result['csv_utf8_bytes'].decode('utf-8-sig'),newline='')))

class ExportTests(unittest.TestCase):
 def test_explicit_order_and_subset(self):
  r=build_transaction_csv([row()],fields=['currency','amount']);self.assertEqual(decoded(r),[['currency','amount'],['EUR',"'-12.40"]]);self.assertEqual(r['fields'],['currency','amount'])
 def test_header_only_empty(self):self.assertEqual(decoded(build_transaction_csv([],fields=['amount'])),[['amount']])
 def test_bom_and_crlf(self):
  b=build_transaction_csv([row()],fields=['currency'])['csv_utf8_bytes'];self.assertTrue(b.startswith(b'\xef\xbb\xbf'));self.assertEqual(b.count(b'\r\n'),2)
 def test_formula_markers_after_prefixes(self):
  for prefix in ['', ' ','\t','\r','\n','\v','\f','\ufeff',' \t\r\n\ufeff']:
   for marker in ['=','+','-','@']:
    text=prefix+marker+'SUM(1,1)'
    with self.subTest(text=repr(text)):self.assertEqual(decoded(build_transaction_csv([row(description=text)],fields=['description']))[1][0],"'"+text)
 def test_controls_without_formula(self):
  for prefix in ['\t','\r','\n']:
   self.assertEqual(_cell(prefix+'text'),"'"+prefix+'text')
 def test_unicode_quotes_commas_newlines(self):
  text='Café, "inventado" 🧴\r\nsegunda línea'
  self.assertEqual(decoded(build_transaction_csv([row(description=text)],fields=['description']))[1][0],text)
 def test_safe_strings_not_changed(self):
  for text in ['', '  spaces',"O'Brien","'already",'1+1','line one\nline two']:
   self.assertEqual(_cell(text),text)
 def test_unknown_field_no_leak(self):
  for fields in [['iban'],['account'],['secret'],[],['amount','amount'],['description']*11,None,('amount',),[True]]:
   with self.subTest(fields=fields),self.assertRaises(ExportStopped):build_transaction_csv([row()],fields=fields)
 def test_invalid_rows_generic(self):
  for rows in [None,[],[row(amount='PRIVATE-CANARY')]]:
   if rows==[]:continue
   with self.subTest(rows=rows),self.assertRaises(ExportStopped) as cm:build_transaction_csv(rows,fields=['amount'])
   self.assertNotIn('PRIVATE-CANARY',str(cm.exception));self.assertIsNone(cm.exception.__context__)
 def test_refuses_invalid_even_unselected_field(self):
  with self.assertRaises(ExportStopped):build_transaction_csv([row(iban='synthetic')],fields=['amount'])
 def test_unknown_dates_and_missing_categories_blank(self):
  r=build_transaction_csv([row(date=None,date_source=None)],fields=['date','user_category']);self.assertEqual(decoded(r)[1],['',''])
 def test_bounds_bytes_not_just_characters(self):
  with self.assertRaises(ExportStopped):build_transaction_csv([row(description='🧴'*1024)]*300,fields=['description'])
 def test_all_text_columns_defended(self):
  r=build_transaction_csv([row(description='=x',user_category='@x',provider_category='+x')],fields=['description','user_category','provider_category'])
  self.assertTrue(all(x.startswith("'") for x in decoded(r)[1]))
 def test_scope_no_history_or_dedup_claim(self):
  r=build_transaction_csv([row(),row()],fields=['amount']);self.assertEqual(r['rows'],2);self.assertEqual(r['scope'],'supplied_rows_only');self.assertEqual(r['history_completeness'],'not_verified');self.assertEqual(r['deduplication'],'not_performed')
 def test_no_mutation_and_no_global_destination(self):
  fields=['amount'];records=[row()];before=[dict(records[0])];r=build_transaction_csv(records,fields=fields);self.assertEqual(records,before);r['fields'].append('description');self.assertEqual(fields,['amount'])
 def test_surrogate_refuses_generic(self):
  with self.assertRaises(ExportStopped):build_transaction_csv([row(description='\ud800')],fields=['description'])

if __name__=='__main__':unittest.main()
