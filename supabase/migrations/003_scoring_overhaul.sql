-- Scoring overhaul: unified demand curve across standalone, due-date, and recurring items.

-- importance drives how fast standalone items climb the age curve (1=slow, 5=fast).
ALTER TABLE items
    ADD COLUMN importance integer NOT NULL DEFAULT 3
        CHECK (importance BETWEEN 1 AND 5);

-- lead_time_days controls how early due-date items start ramping up.
ALTER TABLE categories
    ADD COLUMN lead_time_days integer NOT NULL DEFAULT 7
        CHECK (lead_time_days > 0);
