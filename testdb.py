import pymysql.cursors

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             database='spice_bazaar',
                             cursorclass=pymysql.cursors.DictCursor)

try:
    with connection.cursor() as cursor:
        sql = """
        SELECT s.Subcat_id, c.Cat_name, s.Subcat_name, s.Subcat_desc, s.Subcat_status
        FROM tbl_subcategory s
        JOIN tbl_category c ON s.Cat_id = c.Cat_id
        """
        cursor.execute(sql)
        result = cursor.fetchall()
        print(result)  # Debug output
finally:
    connection.close()