CREATE TABLE media (
	site_id TEXT primary key,
	url TEXT
);


CREATE TABLE news (
	site_id TEXT references media,
	url TEXT primary key,
	title TEXT,
	publish_date timestamp,
	topic TEXT,
	popularity TEXT,
	content TEXT,
	tags TEXT
);

INSERT INTO media VALUES ("NOVAYA", "https://www.novayagazeta.ru/"),
	("LENTA", "https://lenta.ru"), ("RIA", "https://ria.ru");