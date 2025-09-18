-- =====================================================
-- MoMo SMS Data Processing System - Database Schema
-- =====================================================
-- Created for Week 2 Assignment: Database Foundation
-- Author: Team Portfolio
-- Date: Sept 2025

-- Drop existing database if it exists (for development)
DROP DATABASE IF EXISTS database_setup;
CREATE DATABASE database_setup;
USE database_setup;

# user table
CREATE TABLE `User` (
  `UserID` INT AUTO_INCREMENT,
  `Name` VARCHAR(100) NOT NULL,
  `Phone` VARCHAR(20) NOT NULL,
  `Email` VARCHAR(100) UNIQUE NOT NULL,
  PRIMARY KEY (`UserID`),
  INDEX (`Email`),
  INDEX (`Phone`)
);

# Message table
CREATE TABLE `Message` (
  `MessageID` INT AUTO_INCREMENT,
  `Raw_text` TEXT NOT NULL,
  `Time` DATETIME NOT NULL,
  `UserID` INT,
  PRIMARY KEY (`MessageID`),
  FOREIGN KEY (`UserID`)
      REFERENCES `User`(`UserID`),
  INDEX (Time)
);

# Transaction table
CREATE TABLE `Transaction` (
  `TransactionID` INT AUTO_INCREMENT,
  `UserID` INT,
  `MessageID` INT,
  `CategoryID` INT,
  `Amount` DECIMAL(15,2) NOT NULL,
  `Currency` VARCHAR(10) DEFAULT 'RWF',
  `Date` DATETIME NOT NULL,
  `Type` ENUM('Deposit', 'Withdrawal', 'Transfer', 'Payment', 'Utility', 'Airtime', 'Received') NOT NULL,
  `Status` VARCHAR(100),
  `Balance` DECIMAL(15,2),
  `Charge` DECIMAL(15,2),
  PRIMARY KEY (`TransactionID`),
  FOREIGN KEY (`MessageID`)
      REFERENCES `Message`(`MessageID`),
  FOREIGN KEY (`UserID`) REFERENCES `User`(`UserID`),
  FOREIGN KEY (`MessageID`) REFERENCES `Message`(`MessageID`),
  INDEX (Type),
  INDEX (Currency),
  INDEX (MessageID)
);

# Transaction category table (Deposit, Payment,...)
CREATE TABLE `Category` (
  `CategoryID` INT AUTO_INCREMENT,
  `Name` VARCHAR(100) NOT NULL ,
  `Description` TEXT,
  PRIMARY KEY (`CategoryID`),
  INDEX (`Name`)
);

# System logs table
CREATE TABLE `System_logs` (
  `LogID` INT AUTO_INCREMENT,
  `Log_level` ENUM('Info', 'Urgent', 'Error', 'Debug') NOT NULL ,
  `Log_category` VARCHAR(100) NOT NULL ,
  `Details` TEXT,
  `UserID` INT,
  `TransactionID` INT,
  `Processing_time` DATETIME,
  `Created_at` DATETIME,
  PRIMARY KEY (`LogID`),
  FOREIGN KEY (`TransactionID`)
      REFERENCES `Transaction`(`TransactionID`),
  FOREIGN KEY (UserID) REFERENCES User(UserID),
  INDEX (Log_level),
  INDEX (TransactionID)
);

