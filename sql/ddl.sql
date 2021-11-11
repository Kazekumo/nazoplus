create table puzzle
(
    id              int      not null
        primary key auto_increment,
    name            varchar(255) not null,
    unlock_score    int      not null,
    score           int      not null,
    tried_num       int      not null,
    passed_num      int      not null,
    author          varchar(255),
    answer          varchar(255) not null,
    unique_template boolean default false
);
create table submission
(
    id          int not null
        primary key auto_increment,
    user        int not null,
    puzzle      int not null,
    accepted    boolean not null,
    create_time datetime
);
create table user
(
    id            int not null
        primary key auto_increment,
    nickname      varchar(64),
    email         varchar(64),
    password_hash varchar(128),
    credit        decimal(10,2) default 0,
    passed_num    int default 0
);