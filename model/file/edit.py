from BaseHandler import *
from FileDB import FileService

def date2str(d):
    ct = time.gmtime(d / 1000)
    return time.strftime('%Y-%m-%d %H:%M:%S', ct)


def try_decode(bytes):
    try:
        return bytes.decode("utf-8")
    except:
        return bytes.decode("gbk")

class handler(BaseFileHandler):

    def default_request(self):
        service = FileService.instance()
        id = self.get_argument("id", None)
        name = self.get_argument("name", None)
        if id is None and name is None:
            raise HTTPError(504)
        if id is not None:
            id = int(id)
            service.visitById(id)
            file = service.getById(id)
        elif name is not None:
            file = service.getByName(name)
        if file is None:
            raise web.notfound()
        download_csv = file.related != None and "CODE-CSV" in file.related
        self.render("file-edit.html", 
            file=file, 
            content = file.get_content(), 
            date2str=date2str,
            download_csv = download_csv, 
            children = FileDB.get_children_by_id(file.id))

    def download_request(self):
        service = FileService.instance()
        id = self.get_argument("id")
        file = service.getById(id)
        content = file.get_content()
        if content.startswith("```CSV"):
            content = content[7:-3] # remove \n
        web.ctx.headers.append(("Content-Type", 'application/octet-stream'))
        web.ctx.headers.append(("Content-Disposition", "attachment; filename=%s.csv" % quote(file.name)))
        return content

    def upload_request(self):
        x = web.input(file = {})
        id = self.get_argument("id")
        if 'file' in x:
            content = try_decode(x.file.file.read())
            content = "```CSV\n" + content + "```"
            service = FileService.instance()
            service.updateContent(id, content)
        raise web.seeother("/file/edit?id=" + id)

    def updateContentRequest(self):
        id = self.get_argument("id")
        content = self.get_argument("content")
        service = FileService.instance()
        file = service.getById(int(id))
        assert file is not None
        service.updateContent(id, content)
        raise web.seeother("/file/edit?id=" + id)