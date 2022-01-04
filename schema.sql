DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `leader_card_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` bigint NOT NULL AUTO_INCREMENT,
  `live_id` bigint NOT NULL,
  `joined_user_count` bigint NOT NULL,
  `status` int NOT NULL DEFAULT 1,
  PRIMARY KEY (`room_id`)
);

DROP TABLE IF EXISTS `room_user`;
CREATE TABLE `room_user` (
  `room_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `leader_card_id` int DEFAULT NULL,
  `select_difficulty` int NOT NULL,
  `is_host` boolean NOT NULL,
  `judge_count_perfect` int DEFAULT 0,
  `judge_count_great` int DEFAULT 0,
  `judge_count_good` int DEFAULT 0,
  `judge_count_bad` int DEFAULT 0,
  `judge_count_miss` int DEFAULT 0,
  `score` int DEFAULT 0,
  PRIMARY KEY (`room_id`, `user_id`)
);
