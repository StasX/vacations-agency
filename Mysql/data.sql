-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 21, 2026 at 04:01 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `vacation_agency`
--
CREATE DATABASE IF NOT EXISTS `vacation_agency` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `vacation_agency`;

DELIMITER $$
--
-- Procedures
--
CREATE DEFINER=`root`@`localhost` PROCEDURE `add_user` (IN `first_name` VARCHAR(15), IN `last_name` VARCHAR(15), IN `an_email` VARCHAR(30), IN `a_password` VARCHAR(128), IN `a_role_id` INT(11))   BEGIN
	INSERT INTO users (first_name, last_name, email, password, role_id) VALUES (first_name, last_name, an_email, a_password, a_role_id);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `add_vacation` (IN `a_country_id` INT(11), IN `a_description` VARCHAR(500), IN `a_start_date` DATE, IN `an_end_date` DATE, IN `a_price` FLOAT(7,2), IN `an_image` VARCHAR(50))   BEGIN
	INSERT INTO vacations(country_id, description,start_date,end_date,price,image) VALUES (a_country_id, a_description, a_start_date, an_end_date, a_price, an_image);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `get_all_vacations` (IN `user_id` INT(11))   BEGIN
	SELECT 
    	vacations.id AS id,
    	countries.name,
    	vacations.description,
    	vacations.start_date,
    	vacations.end_date,
    	vacations.price,
    	vacations.image,
    	COUNT(likes.vacation_id) AS likes_count,
    	EXISTS(SELECT * FROM likes WHERE likes.vacation_id=vacations.id AND likes.user_id=user_id) AS liked 
	FROM vacations CROSS JOIN countries ON vacations.country_id = countries.id LEFT JOIN likes ON vacations.id = likes.vacation_id
	GROUP BY
    	vacations.id,
    	countries.name,
    	vacations.description,
    	vacations.start_date,
    	vacations.end_date,
    	vacations.price,
    	vacations.image
	ORDER BY 
    	vacations.start_date;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `get_likes_count` (`a_vacation_id` INT(11))   BEGIN
	SELECT COUNT(*) AS likes_count FROM likes WHERE vacation_id = a_vacation_id;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `get_user` (IN `an_email` VARCHAR(50), IN `a_password` VARCHAR(128))   BEGIN
	SELECT id, first_name, last_name, email, password, role_id AS role FROM users WHERE email=an_email AND password=a_password;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `is_email_exists` (IN `an_email` VARCHAR(30))   BEGIN
	SELECT COUNT(*) FROM users WHERE email = an_email;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `like_vacation` (`userId` INT(11), `vacationId` INT(11))   BEGIN
   IF (SELECT EXISTS(SELECT * FROM likes WHERE user_id = userId AND vacation_id = vacationId)) THEN
      DELETE FROM likes WHERE user_id = userId AND vacation_id = vacationId;
   ELSE
      INSERT INTO likes VALUES(userId, vacationId);
   END IF;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `remove_vacation` (IN `vacation_id` INT(11))   BEGIN
	DELETE FROM vacations WHERE id = vacation_id;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `update_vacation` (IN `an_id` INT(11), IN `a_country_id` VARCHAR(50), IN `a_description` VARCHAR(500), IN `a_start_date` DATE, IN `an_end_date` DATE, IN `a_price` FLOAT(7,2), IN `an_image` VARCHAR(50))   BEGIN
-- Update vacation
	UPDATE vacations SET country_id = a_country_id, description = a_description, start_date = a_start_date, end_date = an_end_date, price = a_price, image = an_image, description = a_description, start_date = a_start_date, end_date = an_end_date, price = a_price, image = an_image WHERE id = an_id;
END$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `countries`
--
-- Creation: Oct 21, 2026 at 01:29 PM
-- Last update: Oct 21, 2026 at 01:29 PM
--

CREATE TABLE IF NOT EXISTS `countries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- RELATIONSHIPS FOR TABLE `countries`:
--

--
-- Dumping data for table `countries`
--

INSERT INTO `countries` (`id`, `name`) VALUES
(1, 'Greece'),
(2, 'Japan'),
(3, 'Italy'),
(4, 'Swiss'),
(5, 'Australia'),
(6, 'USA'),
(7, 'New Zealand'),
(8, 'Spain'),
(9, 'Thailand'),
(10, 'France'),
(11, 'Israel'),
(12, 'Portugal');

-- --------------------------------------------------------

--
-- Table structure for table `likes`
--
-- Creation: Oct 21, 2026 at 01:32 PM
-- Last update: Oct 21, 2026 at 01:32 PM
--

CREATE TABLE IF NOT EXISTS `likes` (
  `user_id` int(11) NOT NULL,
  `vacation_id` int(11) NOT NULL,
  PRIMARY KEY (`user_id`,`vacation_id`),
  KEY `vacation_id` (`vacation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- RELATIONSHIPS FOR TABLE `likes`:
--

--
-- Dumping data for table `likes`
--

INSERT INTO `likes` (`user_id`, `vacation_id`) VALUES
(1, 6),
(2, 1),
(2, 6);

-- --------------------------------------------------------

--
-- Table structure for table `roles`
--
-- Creation: Oct 21, 2026 at 01:41 PM
-- Last update: Oct 21, 2026 at 01:41 PM
--

CREATE TABLE IF NOT EXISTS `roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `role_type` varchar(20) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- RELATIONSHIPS FOR TABLE `roles`:
--

--
-- Dumping data for table `roles`
--

INSERT INTO `roles` (`id`, `role_type`) VALUES
(1, 'Admin'),
(2, 'User');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--
-- Creation: Oct 21, 2026 at 01:44 PM
-- Last update: Oct 21, 2026 at 01:44 PM
--

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `first_name` varchar(15) NOT NULL,
  `last_name` varchar(15) NOT NULL,
  `email` varchar(30) NOT NULL,
  `password` varchar(128) NOT NULL,
  `role_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `role_id` (`role_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- RELATIONSHIPS FOR TABLE `users`:
--

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `first_name`, `last_name`, `email`, `password`, `role_id`) VALUES
(1, 'Adam', 'Adams', 'adams@mail.com', 'bb182ebb0c316ccb3d88eabbd4157cb19b74ad65ad6fde26db190753803ec9fe52a657f92a52590fc2e76c74fd058b50f9e28827fdca8205002c2d493558e0e4', 1),
(2, 'John', 'Johnson', 'johnson@mail.com', 'bb182ebb0c316ccb3d88eabbd4157cb19b74ad65ad6fde26db190753803ec9fe52a657f92a52590fc2e76c74fd058b50f9e28827fdca8205002c2d493558e0e4', 2),
(9, 'Joe', 'Doe', 'joe@mail.com', 'bb182ebb0c316ccb3d88eabbd4157cb19b74ad65ad6fde26db190753803ec9fe52a657f92a52590fc2e76c74fd058b50f9e28827fdca8205002c2d493558e0e4', 2),
(10, 'Avi', 'Ron', 'avi@email.com', 'bb182ebb0c316ccb3d88eabbd4157cb19b74ad65ad6fde26db190753803ec9fe52a657f92a52590fc2e76c74fd058b50f9e28827fdca8205002c2d493558e0e4', 2);

-- --------------------------------------------------------

--
-- Table structure for table `vacations`
--
-- Creation: Oct 21, 2026 at 01:45 PM
-- Last update: Oct 21, 2026 at 01:45 PM
--

CREATE TABLE IF NOT EXISTS `vacations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `country_id` int(11) NOT NULL,
  `description` varchar(500) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `price` float(7,2) NOT NULL,
  `image` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `country_id` (`country_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- RELATIONSHIPS FOR TABLE `vacations`:
--

--
-- Dumping data for table `vacations`
--

INSERT INTO `vacations` (`id`, `country_id`, `description`, `start_date`, `end_date`, `price`, `image`) VALUES
(1, 9, 'Discover the allure of Phuket, a tropical haven where turquoise waters meet golden sands. Immerse yourself in luxury resorts, indulge in vibrant nightlife on Patong\'s Bangla Road, and explore the cultural charm of Old Phuket Town. From island-hopping adventures to serene beach retreats, Phuket offers a perfect blend of relaxation and excitement in Thailand\'s paradise.', '2024-03-01', '2024-03-16', 6000.00, 'Phuket.jpg'),
(2, 2, 'Embark on a Tokyo getaway, where futuristic skyscrapers coexist with ancient temples. Dive into the buzzing energy of Shibuya and Shinjuku, witness the serenity of Meiji Shrine, and indulge in authentic sushi delights. From the neon-lit streets to tranquil cherry blossom gardens, Tokyo is a captivating blend of modernity and tradition, promising a unique and unforgettable vacation.', '2024-02-10', '2024-02-21', 8000.00, 'Tokyo.jpg'),
(3, 1, 'Escape to Santorini, a Grecian paradise where white-washed buildings cling to volcanic cliffs above the deep blue Aegean Sea. Immerse yourself in breathtaking sunsets over Oia, wander through charming villages with narrow cobblestone streets, and relax on black sand beaches. With its iconic blue-domed churches and unparalleled views, Santorini promises an idyllic escape where beauty unfolds at every turn.', '2024-03-29', '2024-04-13', 7000.00, 'Santorini.jpg'),
(4, 3, 'Embark on a Roman holiday, where ancient history meets modern allure. Stroll through the Colosseum\'s grandeur, toss a coin into the Trevi Fountain for luck, and savor authentic pasta in charming trattorias. Explore the Vatican City\'s treasures and embrace the vibrant life of the Eternal City. In Rome, each cobblestone street tells a story, and every corner echoes with the whispers of a rich and timeless past.', '2024-06-05', '2024-06-13', 9000.00, 'Rome.jpg'),
(5, 6, 'Experience the heartbeat of the Big Apple. Skyscrapers kiss the sky, Central Park invites serenity, and Times Square pulsates with energy. From Broadway\'s dazzling lights to the iconic Statue of Liberty, New York City is a kaleidoscope of culture, cuisine, and endless possibilities. Immerse yourself in the city that never sleeps for a vacation that resonates with the rhythm of metropolitan magic.', '2023-12-28', '2023-12-08', 9500.00, 'NewYork.jpg'),
(6, 6, 'Bask in the glamour of Los Angeles, where palm-lined boulevards lead to sandy beaches and Hollywood stars grace the sidewalks. Explore the iconic Walk of Fame, soak up the sun in Malibu, and indulge in diverse culinary delights. From the allure of Beverly Hills to the vibrant arts scene in Downtown LA, experience the magic of a city that seamlessly blends fame, fashion, and laid-back California cool.', '2024-06-06', '2024-06-22', 9990.00, 'LosAngeles.jpg'),
(7, 4, 'Escape to the Alps, a haven of snow-capped peaks, lush meadows, and crisp mountain air. Whether skiing down pristine slopes in winter or hiking through wildflower-filled valleys in summer, the Alps offer an enchanting blend of adventure and serenity. Experience cozy alpine villages, savor hearty cuisine, and immerse yourself in the breathtaking landscapes that define this idyllic mountain retreat.', '2023-12-23', '2024-01-13', 5000.00, 'Alps.jpg'),
(8, 11, 'Journey to Eilat, a gem nestled by the Red Sea, where sun-drenched beaches meet vibrant coral reefs. Immerse yourself in underwater wonders while snorkeling or diving, then unwind in luxury resorts along the waterfront. Explore the scenic Negev Desert, visit the vibrant Coral Beach Nature Reserve, and savor the unique blend of Israeli hospitality and resort-style relaxation in this sun-soaked paradise.', '2024-04-01', '2024-04-18', 6000.00, 'Eilat.jpg'),
(9, 8, 'Escape to Barcelona, where Gaudí\'s masterpieces grace the skyline, and the Mediterranean breeze invites exploration. Wander along La Rambla, indulge in tapas at bustling markets, and marvel at the architectural wonders of Sagrada Família. From the historic Barri Gòtic to the sun-kissed beaches, Barcelona is a vibrant tapestry of culture, art, and seaside allure.', '2024-06-07', '2024-06-15', 8500.00, 'Barcelona.jpg'),
(10, 1, 'Discover the allure of Crete, the largest Greek island, where ancient myths intertwine with stunning landscapes. Explore Minoan ruins at Knossos, wander through charming villages with whitewashed houses, and relax on pristine beaches kissed by the Mediterranean sun. With a blend of rich history, warm hospitality, and breathtaking scenery, Crete invites you to experience a vacation that is both timeless and unforgettable.', '2024-05-03', '2024-03-14', 7500.00, 'Crete.jpg'),
(11, 10, 'Savor the enchantment of Paris, where iconic landmarks like the Eiffel Tower and Louvre Museum grace the cityscape. Stroll along the Seine River, indulge in delectable pastries at charming cafés, and immerse yourself in art and history. With its romantic ambiance, world-class cuisine, and timeless charm, Paris is an exquisite tapestry of culture and sophistication, promising a vacation filled with unforgettable moments.', '2024-05-17', '2024-05-18', 3500.00, 'Paris.jpg'),
(12, 7, 'Escape to the South Island, a pristine haven where snow-capped peaks, turquoise lakes, and lush fjords create a breathtaking landscape. Explore the adventure capital of Queenstown, cruise through Milford Sound\'s majestic fiords, and hike amid the Southern Alps. With its diverse scenery, outdoor adventures, and warm Kiwi hospitality, the South Island offers a vacation that\'s a symphony of nature\'s wonders.', '2024-01-10', '2024-01-17', 9500.00, 'SouthIsland.jpg');
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
