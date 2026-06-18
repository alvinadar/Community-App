import mysql.connector
mydb = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = "123",
)

print(mydb)

print(mydb.is_connected())

mydb.close()
