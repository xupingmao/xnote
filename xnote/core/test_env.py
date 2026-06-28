
class TestEnv:
    """用于测试的运行时环境"""
    is_test = False
    is_admin = False
    has_login = False
    login_user_name = "test"
    skip_backup = False
    has_backup = False
    
    @classmethod
    def login_admin(cls):
        cls.is_admin = True
        cls.has_login = True
        cls.login_user_name = "admin"
        
    @classmethod
    def login_user(cls, user_name=""):
        cls.is_admin = (user_name == "admin")
        cls.has_login = True
        cls.login_user_name = user_name
        
    @classmethod
    def logout(cls):
        cls.has_login = False
        cls.is_admin = False
