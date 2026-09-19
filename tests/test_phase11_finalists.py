from smartgrid_mlops.finalists.selection import choose_reference,holm
def test_reference_tie_break_and_determinism():
 c=[{'candidate_id':'full','mae':100,'feature_count':12,'complexity':10,'runtime':2},{'candidate_id':'lag','mae':100.4,'feature_count':3,'complexity':2,'runtime':1}]
 assert choose_reference(c)['candidate_id']=='lag'
def test_holm_monotone():
 assert holm([.01,.04,.2])==[.03,.08,.2]
