# QaaS

### How to run

```
make all
```

or

```
docker-compose --build up -d
```

### Tests

```
make test
```

or 

```
docker-compose run --rm qaas pytest /code
```

Base URL:

* http://localhost:8000/api

Swagger

* http://localhost:8000/swagger

Admin

* http://localhost:8000/admin

MailHog (to check invites)

* http://localhost:8025/


# API description

## Navigation

[[Create Quiz](#opIdquizmaker_quizzes_create)]

[[Invite participants](#opIdquizmaker_quizzes_invite)]

[[Quiz progress](#opIdquizmaker_quizzes_progress)]

[[Participants and their scores](#opIdquizmaker_quizzes_participants)]

[[Notify participants about results](#opIdquizmaker_quizzes_notify)]

[[Quizzes](#opIdquizmaker_quizzes_list)]  [[Participants](#opIdquizmaker_quizzes_participants)] [[Invitees](#opIdquizmaker_quizzes_invitees)] [[Questions](#opIdquizmaker_quizzes_questions)] [[Answers](#opIdanswers_list)]  

---

[[Accept invitation](#opIdaccept-invite_read)]

[[Quizzes for participants](#opIdquizzes_list)]

[[Answer a question](#opIdquizzes_answer)]

# Quizmaker

## Create Quiz

<a id="opIdquizmaker_quizzes_create"></a>

```http
POST http://localhost:8000/api/quizmaker/quizzes/ HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json

```

`POST /quizmaker/quizzes/`

> Body parameter
```json
{
  "title": "Test quiz",
  "questions": [
    {
      "answers": [
        {
          "answer": "Answer 1",
          "correct": true
        },
        {
          "answer": "Answer 2"
        }
      ],
      "question": "Question 1",
      "score": 3
    },
  ],
  "description": "Test description",
  "tags": [
      "tag"
  ]
}
```

> Example response
```json
{
    "id": 1,
    "title": "Test quiz",
    "description": "Some description",
    "questions": [
        {
            "id": 1,
            "answers": [
                {
                    "id": 1,
                    "answer": "Answer 1",
                    "correct": true
                },
                {
                    "id": 2,
                    "answer": "Answer 2",
                    "correct": false
                }
            ],
            "score": 1,
            "question": "Question 1"
        },
    ],
    "tags": [
        "tag",
    ]
}
```

## Read quizzes

<a id="opIdquizmaker_quizzes_list"></a>

```http
GET http://localhost:8000/api/quizmaker/quizzes/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizmaker/quizzes/`

`GET /quizmaker/quizzes/?created_after=2022-01-03&created_before=2022-05-03&search=something`

> Example response

```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "tags": [
                "tag",
                "another tag"
            ],
            "created_at": "2022-03-29T16:47:28.570660Z",
            "updated_at": "2022-03-29T16:47:28.570709Z",
            "title": "Test quiz",
            "description": "Some description",
            "slug": "test-quiz"
        },
        {
            "id": 2,
            "tags": [
                "another tag"
            ],
            "created_at": "2022-03-29T16:48:04.926682Z",
            "updated_at": "2022-03-29T16:48:04.926725Z",
            "title": "Test quiz 2",
            "description": "Test 2 description",
            "slug": "test-quiz-2"
        }
    ]
}
```

## Read quiz

<a id="opIdquizmaker_quizzes_read"></a>


```http
GET http://localhost:8000/api/quizmaker/quizzes/{id}/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizmaker/quizzes/{id}/`


> Example response

```json
{
    "id": 1,
    "title": "Test quiz",
    "description": "Some description",
    "questions": [
        {
            "id": 1,
            "answers": [
                {
                    "id": 1,
                    "answer": "Answer 1",
                    "correct": true
                },
                {
                    "id": 2,
                    "answer": "Answer 2",
                    "correct": false
                }
            ],
            "score": 1,
            "question": "Question 1"
        },
    ],
    "tags": [
        "tag",
    ]
}
```

## Quiz - invite participants

<a id="opIdquizmaker_quizzes_invite"></a>


```http
POST http://localhost:8000/api/quizmaker/quizzes/{id}/invite/ HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json

```

`POST /quizmaker/quizzes/{id}/invite/`


> Body parameter

```json
[
    "test3@test.com",
    "test2@test.com"
]
```

> Example response

```json
{
    "valid": [
        {
            "test3@test.com": "invited"
        },
    ],
    "invalid": [
        {
            "test2@test.com": "pending invite"
        },
    ]
}
```


## Quiz - invitees

<a id="opIdquizmaker_quizzes_invitees"></a>


```http
GET http://localhost:8000/api/quizmaker/quizzes/{id}/invitees/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizmaker/quizzes/{id}/invitees/`


> Example response

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "accepted": false,
            "sent": null,
            "email": "test3@test.com"
        },
    ]
}
```


## Quiz - participants

<a id="opIdquizmaker_quizzes_participants"></a>


```http
GET http://localhost:8000/api/quizmaker/quizzes/{id}/participants/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizmaker/quizzes/{id}/participants/`

`GET /quizmaker/quizzes/{id}/participants/?status=completed&email=test@test.com`

Quiz participants and their scores

> Example response

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "email": "tes@test.com",
            "status": "accepted",
            "score_str": "0 out of 7",
            "answered_questions_count": 0
        }
    ]
}
```

## Quiz questions

<a id="opIdquizmaker_quizzes_questions"></a>

```http
GET http://localhost:8000/api/quizmaker/quizzes/{id}/questions/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizmaker/quizzes/{id}/questions/`

`GET /quizmaker/quizzes/{id}/questions/?search=question_name`

> Example response

```json
[
    {
        "id": 1,
        "answers": [
            {
                "id": 1,
                "answer": "Answer 1",
                "correct": true
            },
            {
                "id": 2,
                "answer": "Answer 2",
                "correct": false
            }
        ],
        "score": 1,
        "question": "Question 1"
    }
]
```

## Quiz progress

<a id="opIdquizmaker_quizzes_progress"></a>

```http
GET http://localhost:8000/api/quizmaker/quizzes/{id}/progress/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizmaker/quizzes/{id}/progress/`

> Example response


```json
{
    "invitees_summary": [
        {
            "accepted": false,
            "count": 5
        },
        {
            "accepted": true,
            "count": 1
        }
    ],
    "participants_summary": [
        {
            "status": "accepted",
            "count": 1
        }
    ]
}
```


## Quiz - notify participants

<a id="opIdquizmaker_quizzes_notify"></a>


```http
POST http://localhost:8000/api/quizmaker/quizzes/{id}/notify/ HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json

```

`POST /quizmaker/quizzes/{id}/notify/`

Send notifications with results to those who completed the quiz


> Example response

> 200 Response


## Questions

<a id="opIdquestions_list"></a>


```http
GET http://localhost:8000/api/questions/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /questions/`

`GET /questions/?search=question&quiz={quiz_id}`

> Example response


```json
{
    "count": 6,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "question": "Question 1",
            "score": 1,
            "quiz": 1
        },
        {
            "id": 2,
            "question": "Question 2",
            "score": 3,
            "quiz": 1
        }
    ]
}
```


## Question

<a id="opIdquestions_read"></a>

```http
GET http://localhost:8000/api/questions/{id}/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /questions/{id}/`

> Example response


```json
{
    "id": 1,
    "answers": [
        {
            "id": 1,
            "answer": "Answer 1",
            "correct": true
        },
        {
            "id": 2,
            "answer": "Answer 2",
            "correct": false
        }
    ],
    "score": 1,
    "question": "Question 1"
}
```


## Answers

<a id="opIdanswers_list"></a>

> Code samples

```http
GET http://localhost:8000/api/answers/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /answers/`

`GET /answers/?search=str&question={question_id}`


> Example response


```json
{
  "count": 0,
  "next": "http://example.com",
  "previous": "http://example.com",
  "results": [
    {
      "id": 0,
      "answer": "string",
      "correct": true
    }
  ]
}
```


# Quiz - participant perspective


## Accept invitation

<a id="opIdaccept-invite_read"></a>


```http
GET http://localhost:8000/api/accept-invite/{key}/ HTTP/1.1
Host: localhost:8000

```

`GET /accept-invite/{key}/`

> Example response
```json
{
    "quiz": "/api/quizzes/{id}/?token={key}/"
}
```


## Quizzes

Requires token or authentication

<a id="opIdquizzes_list"></a>

```http
GET http://localhost:8000/api/quizzes/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizzes/?token={token}`


> Example response

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "tags": [
                "tag",
                "another tag"
            ],
            "created_at": "2022-03-29T16:47:28.570660Z",
            "updated_at": "2022-03-29T16:47:28.570709Z",
            "title": "Test quiz",
            "description": "Some description",
            "slug": "test-quiz"
        }
    ]
}
```

## Quiz

Requires token or authentication

<a id="opIdquizzes_read"></a>

```http
GET http://localhost:8000/api/quizzes/{id}/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizzes/{id}/?token={token}`


> Example response


```json
{
    "id": 1,
    "slug": "test-quiz",
    "title": "Test quiz",
    "description": "Some description",
    "questions": [
        {
            "id": 1,
            "question": "Question 1",
            "answers": [
                {
                    "id": 1,
                    "answer": "Answer 1"
                },
                {
                    "id": 2,
                    "answer": "Answer 2"
                }
            ]
        }
    ],
    "tags": [
        "tag",
    ],
    "link": "http://localhost:8000/api/quizzes/1/"
}
```


## Answering the quiz

<a id="opIdquizzes_answer"></a>

```http
POST http://localhost:8000/api/quizzes/{id}/answer/ HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json

```

`POST /quizzes/{id}/answer/?token={token}`


```json
{
  "question": 1,
  "answer": 2
}
```

> Example response

> 201 Response

```json
{
    "answered_questions_count": 1,
    "total_questions_count": 2,
    "remaining_questions": [
        {
            "id": 2,
            "question": "Question 2",
            "answers": [
                {
                    "id": 3,
                    "answer": "Answer 1"
                },
                {
                    "id": 4,
                    "answer": "Answer 2"
                }
            ]
        }
    ]
}
```

> 400 Response 
```json
{
    "__all__": [
        "You have already answered this question"
    ]
}
```

## My progress

Requires token or authentication

<a id="opIdquizzes_progress"></a>


```http
GET http://localhost:8000/api/quizzes/{id}/my-progress/ HTTP/1.1
Host: localhost:8000
Accept: application/json

```

`GET /quizzes/{id}/my-progress/?token={token}`


> Example response

```json
{
  "answered_questions_count": 0,
  "total_questions_count": 0,
  "remaining_questions": [
    {
      "id": 0,
      "question": "string",
      "answers": [
        {
          "id": 0,
          "answer": "string"
        }
      ]
    }
  ]
}
```


# Report

<a id="opIdreport_list"></a>


```http
GET http://localhost:8000/api/report HTTP/1.1
Host: localhost:8000

```

`GET /report`

`GET /report?output_format=json`

`GET /report?output_format=csv`
