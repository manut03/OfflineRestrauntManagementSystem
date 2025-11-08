-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: restaurant_db
-- ------------------------------------------------------
-- Server version	8.0.41

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `categories`
--

DROP TABLE IF EXISTS `categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categories`
--

LOCK TABLES `categories` WRITE;
/*!40000 ALTER TABLE `categories` DISABLE KEYS */;
INSERT INTO `categories` VALUES (4,'Beverages'),(5,'Desserts'),(2,'Fresh Fix'),(3,'Quick Bites');
/*!40000 ALTER TABLE `categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inventory_items`
--

DROP TABLE IF EXISTS `inventory_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventory_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `quantity` decimal(10,2) NOT NULL DEFAULT '0.00',
  `cost_per_unit` decimal(10,2) NOT NULL DEFAULT '0.00',
  `low_stock_threshold` decimal(10,2) DEFAULT '5.00',
  `image` varchar(255) DEFAULT 'default.png',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `inventory_items`
--

LOCK TABLES `inventory_items` WRITE;
/*!40000 ALTER TABLE `inventory_items` DISABLE KEYS */;
INSERT INTO `inventory_items` VALUES (1,'Sugar',53.00,50.00,5.00,'sugar.png'),(2,'Coffee Beans',20.00,150.00,5.00,'coffee_beans.png'),(3,'Milk',2.00,30.00,5.00,'milk.png'),(4,'Maida',3.00,60.00,5.00,'maida.png'),(6,'Cocoa Powder',42.00,150.00,5.00,'cocoa_powder.png'),(7,'Fish Meat',6.00,50.00,5.00,'FishMeat.jpeg'),(8,'green tea',0.00,35.00,5.00,'Greentea.png');
/*!40000 ALTER TABLE `inventory_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inventory_transactions`
--

DROP TABLE IF EXISTS `inventory_transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventory_transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_name` varchar(255) NOT NULL,
  `transaction_type` enum('stock_in','stock_out') NOT NULL,
  `quantity` decimal(10,2) NOT NULL,
  `cost_per_unit` decimal(10,2) NOT NULL,
  `transaction_date` datetime NOT NULL,
  `seller` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `item_name` (`item_name`),
  CONSTRAINT `inventory_transactions_ibfk_1` FOREIGN KEY (`item_name`) REFERENCES `inventory_items` (`name`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `inventory_transactions`
--

LOCK TABLES `inventory_transactions` WRITE;
/*!40000 ALTER TABLE `inventory_transactions` DISABLE KEYS */;
INSERT INTO `inventory_transactions` VALUES (1,'Sugar','stock_in',50.00,35.00,'2025-03-01 10:00:00','Supplier A'),(2,'Sugar','stock_in',50.00,40.00,'2025-03-15 14:00:00','Supplier B'),(3,'Sugar','stock_out',20.00,35.00,'2025-03-10 09:00:00','N/A'),(4,'Sugar','stock_out',10.00,40.00,'2025-03-20 16:00:00','N/A'),(5,'Coffee Beans','stock_in',30.00,140.00,'2025-03-05 12:00:00','Supplier C'),(6,'Coffee Beans','stock_in',20.00,150.00,'2025-03-18 11:00:00','Supplier D'),(7,'Coffee Beans','stock_out',15.00,140.00,'2025-03-12 08:00:00','N/A'),(8,'Coffee Beans','stock_out',10.00,150.00,'2025-03-22 15:00:00','N/A'),(9,'Milk','stock_in',60.00,28.00,'2025-03-03 09:00:00','Supplier E'),(10,'Milk','stock_in',40.00,30.00,'2025-03-19 13:00:00','Supplier F'),(11,'Milk','stock_out',25.00,28.00,'2025-03-08 10:00:00','N/A'),(12,'Milk','stock_out',25.00,30.00,'2025-03-23 14:00:00','N/A'),(13,'sugar','stock_out',67.00,40.00,'2025-03-25 19:35:13','N/A'),(14,'Coffee Beans','stock_out',15.00,150.00,'2025-03-26 21:26:59','N/A'),(15,'Milk','stock_out',48.00,30.00,'2025-03-26 21:27:20','N/A'),(16,'Maida','stock_in',50.00,60.00,'2025-03-27 06:33:48','abz sellers'),(17,'Coffee Beans','stock_out',7.00,150.00,'2025-03-27 06:53:06','N/A'),(18,'Maida','stock_out',48.00,60.00,'2025-03-27 06:58:54','N/A'),(19,'Cocoa Powder','stock_in',50.00,150.00,'2025-03-28 04:50:17','AMX'),(20,'Cocoa Powder','stock_out',8.00,150.00,'2025-03-28 04:50:46','N/A'),(21,'Sugar','stock_in',50.00,50.00,'2025-03-28 04:51:21','AMX'),(22,'Maida','stock_in',10.00,60.00,'2025-03-28 05:25:55','AMX'),(23,'Coffee Beans','stock_in',20.00,150.00,'2025-03-28 06:22:46','AMX'),(24,'Coffee Beans','stock_out',3.00,150.00,'2025-03-28 06:23:44','N/A'),(25,'Fish Meat','stock_in',6.00,50.00,'2025-03-28 09:04:05','AMX'),(26,'Maida','stock_out',9.00,60.00,'2025-03-28 09:08:21','N/A'),(27,'green tea','stock_in',20.00,35.00,'2025-08-11 09:30:13','hello traders'),(28,'green tea','stock_out',20.00,35.00,'2025-08-11 09:30:35','N/A');
/*!40000 ALTER TABLE `inventory_transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inventory_usage`
--

DROP TABLE IF EXISTS `inventory_usage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventory_usage` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_name` varchar(255) NOT NULL,
  `quantity_used` decimal(10,2) NOT NULL,
  `used_date` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `inventory_usage`
--

LOCK TABLES `inventory_usage` WRITE;
/*!40000 ALTER TABLE `inventory_usage` DISABLE KEYS */;
/*!40000 ALTER TABLE `inventory_usage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `menu_items`
--

DROP TABLE IF EXISTS `menu_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `menu_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `quantity` int NOT NULL,
  `category_id` int DEFAULT NULL,
  `image` varchar(255) DEFAULT 'coffee.jpg',
  PRIMARY KEY (`id`),
  KEY `fk_category` (`category_id`),
  CONSTRAINT `fk_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu_items`
--

LOCK TABLES `menu_items` WRITE;
/*!40000 ALTER TABLE `menu_items` DISABLE KEYS */;
INSERT INTO `menu_items` VALUES (1,'Coffee',100.00,1,2,'Coffee.jpg'),(2,'Tea',20.00,1,2,'Tea.png'),(3,'Lemon Mocktail',150.00,1,2,'LemonMocktail.png'),(4,'Croissant',150.00,2,3,'Croissant.png'),(5,'Cookie',25.00,1,3,'Cookie.png'),(6,'Veg Wrap',150.00,1,2,'VegWrap.png'),(7,'Chocolate Lava',25.00,1,3,'ChocolateLava.png'),(8,'Sandwich',60.00,6,3,'Sandwich.png'),(10,'Milk Shake (original)',80.00,1,4,'milkshake.jpeg'),(11,'Oreo Milkshake',150.00,1,4,'OreoMilkshake.jpg'),(12,'Vanilla Ice cream',20.00,1,5,'vannila icecream.jpeg'),(13,'Choclate Ice cream',40.00,1,5,'Chocolate.jpeg'),(14,'Green Tea',20.00,1,2,'Greentea.png');
/*!40000 ALTER TABLE `menu_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_items`
--

DROP TABLE IF EXISTS `order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int DEFAULT NULL,
  `item_name` varchar(100) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `quantity` int DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=88 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_items`
--

LOCK TABLES `order_items` WRITE;
/*!40000 ALTER TABLE `order_items` DISABLE KEYS */;
INSERT INTO `order_items` VALUES (1,1,'Coffee',5.00,1),(2,1,'Tea',3.50,1),(3,1,'crossiant',10.00,1),(4,2,'Coffee',5.00,1),(5,2,'idli',50.00,1),(6,2,'crossiant',10.00,1),(7,3,'Tea',3.50,2),(8,3,'crossiant',10.00,1),(9,4,'Coffee',5.00,1),(10,4,'Tea',3.50,2),(11,4,'crossiant',10.00,1),(12,4,'idli',50.00,1),(13,5,'Coffee',5.00,3),(14,6,'Coffee',5.00,3),(15,7,'Coffee',5.00,3),(16,7,'Tea',3.50,1),(17,8,'crossiant',10.00,3),(18,9,'Coffee',5.00,2),(19,9,'idli',50.00,2),(20,10,'Tea',3.50,6),(21,11,'Coffee',20.00,8),(22,12,'Coffee',90.00,7),(23,13,'Tea',20.00,1),(24,13,'Cookie',25.00,2),(25,13,'Crossiant',150.00,1),(26,13,'Lemon Mocktail',150.00,1),(27,13,'Green Tea',25.00,3),(28,14,'Coffee',90.00,3),(29,14,'Lemon Mocktail',150.00,2),(30,14,'Veg Wrap',150.00,1),(31,15,'Tea',20.00,4),(32,16,'Coffee',90.00,13),(33,17,'Lemon Mocktail',150.00,5),(34,18,'Crossiant',150.00,1),(35,18,'Cookie',25.00,1),(36,18,'Sandwich',60.00,1),(37,18,'Chocolate Lava',25.00,3),(38,19,'Cookie',25.00,6),(39,20,'Coffee',90.00,4),(40,20,'Tea',20.00,1),(41,20,'Lemon Mocktail',150.00,2),(42,21,'Lemon Mocktail',150.00,5),(43,22,'Tea',20.00,3),(44,23,'Coffee',90.00,4),(45,23,'Cookie',25.00,1),(46,24,'Lemon Mocktail',150.00,4),(47,25,'Cookie',25.00,1),(48,26,'Coffee',100.00,2),(49,27,'Croissant',150.00,1),(50,28,'Tea',20.00,2),(51,28,'Cookie',25.00,1),(52,29,'Cookie',25.00,2),(53,29,'Tea',20.00,1),(54,30,'Chocolate Lava',25.00,4),(55,31,'Coffee',100.00,4),(56,32,'Tea',20.00,2),(57,33,'Coffee',100.00,6),(58,33,'Tea',20.00,1),(59,33,'Croissant',150.00,1),(60,33,'Milk Shake (original)',80.00,1),(61,34,'Coffee',100.00,4),(62,34,'Lemon Mocktail',150.00,2),(63,35,'Cookie',25.00,3),(64,35,'Veg Wrap',150.00,1),(65,36,'Croissant',150.00,2),(66,36,'Sandwich',60.00,1),(67,37,'Veg Wrap',150.00,1),(68,38,'Tea',20.00,5),(69,39,'Tea',20.00,4),(70,40,'Tea',20.00,3),(71,41,'Oreo Milkshake',150.00,3),(72,42,'Croissant',150.00,1),(73,43,'Cookie',25.00,4),(74,44,'Croissant',150.00,2),(75,44,'Cookie',25.00,2),(76,45,'Tea',20.00,2),(77,45,'Vanilla Ice cream',20.00,1),(78,45,'Chocolate Lava',25.00,1),(79,46,'Vanilla Ice cream',20.00,2),(80,46,'Coffee',100.00,2),(81,47,'Lemon Mocktail',150.00,2),(82,48,'Lemon Mocktail',150.00,2),(83,49,'Chocolate Lava',25.00,1),(84,49,'Oreo Milkshake',150.00,2),(85,50,'Coffee',100.00,1),(86,51,'Tea',20.00,2),(87,52,'Chocolate Lava',25.00,1);
/*!40000 ALTER TABLE `order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_number` varchar(20) NOT NULL,
  `subtotal` decimal(10,2) DEFAULT '0.00',
  `taxes` decimal(10,2) DEFAULT '0.00',
  `total` decimal(10,2) DEFAULT '0.00',
  `payment_method` varchar(50) DEFAULT NULL,
  `status` enum('pending','completed','cancelled') DEFAULT 'pending',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_number` (`order_number`)
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
INSERT INTO `orders` VALUES (1,'QFLK4TUA',18.50,1.85,20.35,NULL,'cancelled','2025-03-24 14:32:27'),(2,'EWWG5XLG',65.00,6.50,71.50,NULL,'cancelled','2025-03-24 14:33:40'),(3,'20250324-003',17.00,1.70,18.70,NULL,'cancelled','2025-03-24 14:51:29'),(4,'20250324-004',72.00,7.20,79.20,NULL,'cancelled','2025-03-24 14:59:03'),(5,'20250324-005',15.00,1.50,16.50,NULL,'pending','2025-03-24 15:03:42'),(6,'20250324-006',15.00,1.50,16.50,NULL,'cancelled','2025-03-24 15:04:32'),(7,'20250324-007',18.50,1.85,20.35,NULL,'cancelled','2025-03-24 15:10:13'),(8,'20250324-008',30.00,3.00,33.00,NULL,'pending','2025-03-24 15:13:05'),(9,'20250324-009',110.00,11.00,121.00,'cash','completed','2025-03-24 15:18:09'),(10,'20250324-010',21.00,2.10,23.10,'cash','completed','2025-03-24 15:26:58'),(11,'20250324-011',160.00,16.00,176.00,'cash','completed','2025-03-24 15:58:59'),(12,'20250325-001',630.00,63.00,693.00,'cash','completed','2025-03-24 20:03:26'),(13,'20250325-002',445.00,44.50,489.50,'cash','completed','2025-03-24 20:04:07'),(14,'20250325-003',720.00,72.00,792.00,'cash','completed','2025-03-24 22:07:44'),(15,'20250325-004',80.00,8.00,88.00,'cash','completed','2025-03-24 22:09:03'),(16,'20250325-005',1170.00,117.00,1287.00,'cash','completed','2025-03-24 22:21:48'),(17,'20250325-006',750.00,75.00,825.00,'cash','completed','2025-03-24 22:22:19'),(18,'20250325-007',310.00,31.00,341.00,'cash','completed','2025-03-24 22:23:04'),(19,'20250325-008',150.00,15.00,165.00,'cash','completed','2025-03-24 22:23:14'),(20,'20250325-009',680.00,68.00,748.00,'cash','completed','2025-03-25 13:32:56'),(21,'20250325-010',750.00,75.00,825.00,'cash','completed','2025-03-25 13:48:14'),(22,'20250325-011',60.00,6.00,66.00,'cash','completed','2025-03-25 13:53:07'),(23,'20250325-012',385.00,38.50,423.50,'cash','completed','2025-03-25 14:05:27'),(24,'20250325-013',600.00,60.00,660.00,'cash','completed','2025-03-25 17:32:44'),(25,'20250325-014',25.00,2.50,27.50,'cash','completed','2025-03-25 17:34:36'),(26,'20250325-015',200.00,20.00,220.00,'cash','completed','2025-03-25 18:02:06'),(27,'20250326-001',150.00,15.00,165.00,'cash','completed','2025-03-25 20:47:12'),(28,'20250326-002',65.00,6.50,71.50,'cash','completed','2025-03-25 21:52:58'),(29,'20250326-003',70.00,7.00,77.00,'cash','completed','2025-03-25 21:53:29'),(30,'20250326-004',100.00,10.00,110.00,'cash','completed','2025-03-25 22:41:58'),(31,'20250326-005',400.00,40.00,440.00,'cash','completed','2025-03-26 11:17:54'),(32,'20250326-006',40.00,4.00,44.00,'cash','completed','2025-03-26 14:29:09'),(33,'20250327-001',850.00,85.00,935.00,'cash','pending','2025-03-27 04:21:04'),(34,'20250327-002',700.00,70.00,770.00,'cash','pending','2025-03-27 04:33:34'),(35,'20250327-003',225.00,22.50,247.50,'cash','pending','2025-03-27 16:08:38'),(36,'20250328-001',360.00,36.00,396.00,'cash','completed','2025-03-27 18:36:58'),(37,'20250328-002',150.00,15.00,165.00,'cash','completed','2025-03-27 18:38:24'),(38,'20250328-003',100.00,10.00,110.00,'cash','completed','2025-03-27 18:39:30'),(39,'20250328-004',80.00,8.00,88.00,'cash','completed','2025-03-27 21:54:20'),(40,'20250328-005',60.00,6.00,66.00,'cash','completed','2025-03-27 23:22:11'),(41,'20250328-006',450.00,45.00,495.00,'cash','completed','2025-03-27 23:55:18'),(42,'20250328-007',150.00,15.00,165.00,'cash','completed','2025-03-28 00:10:20'),(43,'20250328-008',100.00,10.00,110.00,'cash','completed','2025-03-28 00:54:06'),(44,'20250328-009',350.00,35.00,385.00,'cash','completed','2025-03-28 00:55:24'),(45,'20250328-010',85.00,8.50,93.50,'cash','pending','2025-03-28 03:27:54'),(46,'20250328-011',240.00,24.00,264.00,'cash','pending','2025-03-28 03:28:57'),(47,'20250328-012',300.00,30.00,330.00,'cash','pending','2025-03-28 03:29:20'),(48,'20250328-013',300.00,30.00,330.00,'cash','pending','2025-03-28 03:30:04'),(49,'20250810-001',325.00,32.50,357.50,'cash','pending','2025-08-10 16:30:51'),(50,'20250811-001',100.00,10.00,110.00,'cash','completed','2025-08-11 04:01:42'),(51,'20250811-002',40.00,4.00,44.00,'cash','completed','2025-08-11 09:06:32'),(52,'20250811-003',25.00,2.50,27.50,'cash','completed','2025-08-11 09:18:39');
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-09  0:48:38
