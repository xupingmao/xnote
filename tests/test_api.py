from .test_base import json_request, json_request_return_dict, BaseTestCase
from .test_base import init as init_app
from xnote_handlers.dict import dict_dao
from xutils import textutil

app = init_app()

class TestMain(BaseTestCase):

    def test_encode(self):
        input_text = "a"
        params = dict(type="sha1", input=input_text)
        result = json_request_return_dict("/api/v1/encode", method="POST", data=params)
        assert result["success"] == True
        assert result.get("data") == textutil.sha1_hex(input_text)