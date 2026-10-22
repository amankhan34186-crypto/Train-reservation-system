CREATE DATABASE IF NOT EXISTS railway_reservation
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE railway_reservation;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS trains (
    train_id INT AUTO_INCREMENT PRIMARY KEY,
    train_number VARCHAR(10) NOT NULL UNIQUE,
    train_name VARCHAR(120) NOT NULL,
    source_station VARCHAR(80) NOT NULL,
    destination_station VARCHAR(80) NOT NULL,
    departure_time TIME NOT NULL,
    arrival_time TIME NOT NULL,
    duration VARCHAR(30) NOT NULL,
    total_seats INT NOT NULL,
    fare DECIMAL(10,2) NOT NULL,
    CHECK (total_seats > 0),
    CHECK (fare >= 0),
    INDEX idx_train_route (source_station, destination_station)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS train_schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    journey_date DATE NOT NULL,
    available_seats INT NOT NULL,
    CONSTRAINT fk_schedule_train FOREIGN KEY (train_id)
        REFERENCES trains(train_id) ON DELETE CASCADE,
    CONSTRAINT uq_train_journey UNIQUE (train_id, journey_date),
    CHECK (available_seats >= 0),
    INDEX idx_schedule_date_route (journey_date, train_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bookings (
    booking_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pnr_number VARCHAR(12) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    schedule_id INT NOT NULL,
    booking_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    number_of_passengers INT NOT NULL,
    total_fare DECIMAL(10,2) NOT NULL,
    booking_status ENUM('CONFIRMED','CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    CONSTRAINT fk_booking_schedule FOREIGN KEY (schedule_id)
        REFERENCES train_schedules(schedule_id),
    CHECK (number_of_passengers BETWEEN 1 AND 6),
    CHECK (total_fare >= 0),
    INDEX idx_booking_user_date (user_id, booking_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS passengers (
    passenger_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    booking_id BIGINT NOT NULL,
    passenger_name VARCHAR(70) NOT NULL,
    age TINYINT UNSIGNED NOT NULL,
    gender ENUM('Male','Female','Other','Prefer not to say') NOT NULL DEFAULT 'Prefer not to say',
    CONSTRAINT fk_passenger_booking FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CHECK (age BETWEEN 1 AND 120),
    INDEX idx_passenger_booking (booking_id)
) ENGINE=InnoDB;

-- Demo trains: illustrative data only, not live Indian Railways data.
INSERT INTO trains
(train_number, train_name, source_station, destination_station, departure_time, arrival_time, duration, total_seats, fare)
VALUES
('12951', 'Mumbai Rajdhani Express', 'Mumbai', 'Delhi', '16:35:00', '08:35:00', '16h 00m', 100, 1850.00),
('12127', 'Intercity Express', 'Mumbai', 'Pune', '06:40:00', '10:05:00', '3h 25m', 100, 420.00),
('11010', 'Deccan Queen', 'Pune', 'Mumbai', '07:15:00', '10:25:00', '3h 10m', 100, 390.00),
('12902', 'Gujarat Mail', 'Mumbai', 'Ahmedabad', '22:00:00', '06:20:00', '8h 20m', 100, 760.00),
('12702', 'Hussain Sagar Express', 'Hyderabad', 'Bengaluru', '16:45:00', '06:10:00', '13h 25m', 100, 950.00),
('12028', 'Shatabdi Express', 'Bengaluru', 'Hyderabad', '06:00:00', '13:10:00', '7h 10m', 100, 1100.00),
('12958', 'Swarn Jayanti Express', 'Ahmedabad', 'Delhi', '18:50:00', '08:15:00', '13h 25m', 100, 1320.00)
ON DUPLICATE KEY UPDATE train_name = VALUES(train_name);

-- Seed schedules for today through the next 14 days. Safe to run repeatedly.
DELIMITER //
CREATE PROCEDURE seed_demo_schedules()
BEGIN
    DECLARE d INT DEFAULT 0;
    WHILE d <= 14 DO
        INSERT INTO train_schedules (train_id, journey_date, available_seats)
        SELECT train_id, DATE_ADD(CURDATE(), INTERVAL d DAY), total_seats
        FROM trains
        ON DUPLICATE KEY UPDATE train_id = VALUES(train_id);
        SET d = d + 1;
    END WHILE;
END//
DELIMITER ;

CALL seed_demo_schedules();
DROP PROCEDURE seed_demo_schedules;
