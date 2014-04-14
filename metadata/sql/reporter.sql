ALTER TABLE metadata_reporter DROP CONSTRAINT metadata_reporter_pkey
ALTER TABLE metadata_reporter ADD PRIMARY KEY (guid)

ALTER TABLE metadata_article DROP CONSTRAINT metadata_article_pkey
ALTER TABLE metadata_article ADD PRIMARY KEY (guid)