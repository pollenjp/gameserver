DATABASE_URI = "mysql://{mysql_user}:{mysql_passwd}@{host}/{mysql_schema}".format(
    mysql_user="webapp",
    mysql_passwd="webapp_no_password",
    host="172.24.0.2",
    # host="172.0.0.1",
    mysql_schema="webapp",
)
