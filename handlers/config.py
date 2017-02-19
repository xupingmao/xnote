from BaseHandler import *

def obj_str(obj):
    if isinstance(obj, list):
        string = "[<br/>"
        for item in obj:
            string += str(item) + "<br/>"
        return string + "]"
    return obj

class handler(BaseHandler):

    def default_request(self):
        html = "<html>"
        html += "<ul>"
        config_dict = config.get_config()
        for key in config_dict:
            html += "<li>{} = {}</li>".format(key, obj_str(config_dict[key]))

        html += "</ul>"
        html += "</html>"
        return html