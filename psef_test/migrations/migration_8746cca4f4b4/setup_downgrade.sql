/* -*- mode: sql; sql-product: postgres; -*- */
INSERT INTO "LTIProvider" (id,
                           key,
                           updates_lti1p1_id)
VALUES ('lti_prov_1', 'key_1', NULL),
       ('lti_prov_2', 'key_2', 'lti_prov_1');
