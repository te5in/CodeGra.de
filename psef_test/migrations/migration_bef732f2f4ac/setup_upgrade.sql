/* -*- mode: sql; sql-product: postgres; -*- */
INSERT INTO "User" (id,
                    username,
                    email,
                    name,
                    lti_user_id)
VALUES (1, 'user1', 'email1', 'User 1', 11),
       (2, 'user2', 'email2', 'User 2', 22),
       (3, 'user3', 'email3', 'User 3', 33),
       (4, 'user4', 'email4', 'User 4', 44),
       (5, 'user5', 'email5', 'User 5', NULL),
       (6, 'user6', 'email6', 'User 6', 66);


INSERT INTO "LTIProvider" (id,
                           key)
VALUES ('lti_prov_1', 'key_1'),
       ('lti_prov_2', 'key_2');


INSERT INTO "Course" (id,
                      name,
                      lti_provider_id,
                      lti_course_id)
VALUES (1, 'course 1', 'lti_prov_1', 'lti_course_1'),
       (2, 'course 2', 'lti_prov_1', 'lti_course_2'),
       (3, 'course 3', 'lti_prov_2', 'lti_course_3'),
       (4, 'non lti course', NULL, NULL);


INSERT INTO "Course_Role" (id,
                           name,
                           "Course_id")
VALUES (1, 'cr1_1', 1),
       (2, 'cr2_1', 1),
       (3, 'cr3_1', 1),
       (4, 'cr4_1', 1),
       (5, 'cr1_2', 2),
       (6, 'cr2_2', 2),
       (7, 'cr3_2', 2),
       (8, 'cr4_2', 2),
       (9, 'cr1_3', 3),
       (10, 'cr2_3', 3),
       (11, 'cr3_3', 3),
       (12, 'cr4_3', 3),
       (13, 'cr1_4', 4);


INSERT INTO "users-courses" (user_id,
                            course_id)
VALUES (1, 1),
       (1, 12),
       (2, 7),
       (3, 11),
       (3, 2),
       (4, 6),
       (5, 13),
       (6, 12);
