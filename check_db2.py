import os
import mysql.connector as m

c = m.connect(
    user=os.environ["MYSQLUSER"],
    password=os.environ["MYSQLPASSWORD"],
    host=os.environ["MYSQLHOST"],
    port=int(os.environ["MYSQLPORT"]),
    database=os.environ["MYSQL_DATABASE"]
)
cur = c.cursor()
cur.execute("SELECT user, host FROM mysql.user WHERE user=%s", ("root",))
print(cur.fetchall())
c.close()
