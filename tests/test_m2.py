from app.modules.m2_nodes.rules import evaluate
def test_real_alias(result): assert result["stages"][1]["rows"][0]["node"]=="ACCEPT"
def test_real_destination_zone(result): assert result["stages"][1]["rows"][0]["zone"]=="Asia/Tokyo"
def test_real_unknown_node(result): assert any(r["reason"]=="UNKNOWN_NODE" for r in result["stages"][1]["quarantine"])
def test_unknown_destination(): assert evaluate([{"node":"ACCEPT","destination":"XX","parcel":"1"}],{})["quarantine"][0]["reason"]=="UNKNOWN_DESTINATION"
def test_missing_parcel(): assert evaluate([{"node":"ACCEPT","destination":"JP","parcel":""}],{})["quarantine"][0]["reason"]=="EMPTY_PARCEL"
def test_all_four_nodes(): assert len(evaluate([{"node":n,"destination":"JP","parcel":"1"} for n in ["收件","起运","清关","妥投"]],{})["rows"])==4
def test_real_preserved_parcel_id(result): assert result["stages"][1]["rows"][0]["parcel"]=="0001"
