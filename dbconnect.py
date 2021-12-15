import pymysql.cursors


def connection():

    # Connect to the database
    conn = pymysql.connect(host='localhost', user='root', password='PASSWORD', database='curious', charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor)
    c = conn.cursor()

    return c, conn

