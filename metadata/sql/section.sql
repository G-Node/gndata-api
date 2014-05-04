--drop schema public cascade;
--create schema public;

ALTER TABLE metadata_value DROP CONSTRAINT metadata_value_pkey CASCADE;
ALTER TABLE metadata_value ADD PRIMARY KEY (guid);

ALTER TABLE metadata_property DROP CONSTRAINT metadata_property_pkey CASCADE;
ALTER TABLE metadata_property ADD PRIMARY KEY (guid);

ALTER TABLE metadata_section DROP CONSTRAINT metadata_section_pkey CASCADE;
ALTER TABLE metadata_section ADD PRIMARY KEY (guid);

ALTER TABLE metadata_document DROP CONSTRAINT metadata_document_pkey CASCADE;
ALTER TABLE metadata_document ADD PRIMARY KEY (guid);

