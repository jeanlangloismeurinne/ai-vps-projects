CREATE TABLE public.emails (
    id integer NOT NULL,
    message_id character varying(512) NOT NULL,
    from_addr character varying(512) NOT NULL,
    to_addr character varying(512) NOT NULL,
    subject text NOT NULL,
    text_body text NOT NULL,
    html_body text NOT NULL,
    received_at timestamp without time zone NOT NULL,
    summary text,
    status character varying(16) NOT NULL,
    summarized_at timestamp without time zone,
    email_id character varying(64)
);
CREATE SEQUENCE public.emails_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.emails_id_seq OWNED BY public.emails.id;
CREATE TABLE public.prompt_versions (
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    prompt text NOT NULL,
    note text NOT NULL,
    is_active boolean NOT NULL
);
CREATE SEQUENCE public.prompt_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.prompt_versions_id_seq OWNED BY public.prompt_versions.id;
ALTER TABLE ONLY public.emails ALTER COLUMN id SET DEFAULT nextval('public.emails_id_seq'::regclass);
ALTER TABLE ONLY public.prompt_versions ALTER COLUMN id SET DEFAULT nextval('public.prompt_versions_id_seq'::regclass);
ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_pkey PRIMARY KEY (id);
CREATE UNIQUE INDEX ix_emails_message_id ON public.emails USING btree (message_id);
CREATE INDEX ix_emails_status ON public.emails USING btree (status);
CREATE INDEX ix_prompt_versions_is_active ON public.prompt_versions USING btree (is_active);
