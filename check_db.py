import mysql.connector as m
c = m.connect(
    user='root',
    password='PPqaDlRnHLTonPsNLRHZjXuQTujgmwSt',
    host='mysql-k4wk.railway.internal',
    port=3306,
    database='railway'
)
cur = c.cursor()
cur.execute("SELECT user, host FROM mysql.user WHERE user='root'")
print(cur.fetchall())
c.close()
