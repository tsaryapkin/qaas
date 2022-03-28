import factory
from factory import fuzzy


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "users.User"

    username = fuzzy.FuzzyText(prefix="user_", length=20)
    email = factory.LazyAttribute(lambda o: "%s@example.org" % o.username)
    password = factory.Sequence(lambda n: "pwd%d" % n)


class QuizFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "quiz.Quiz"

    title = factory.Faker("sentence", nb_words=5, variable_nb_words=True)
    author = factory.SubFactory(UserFactory)
    description = factory.Faker("sentence", nb_words=20, variable_nb_words=True)

    questions = factory.RelatedFactoryList(
        "tests.factories.QuestionFactory", "quiz", size=3
    )


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "quiz.Question"

    quiz = factory.SubFactory(QuizFactory, questions=[])
    question = factory.Faker("sentence", nb_words=20, variable_nb_words=True)

    @factory.post_generation
    def answers(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for item in extracted:
                self.answers.add(item)


class AnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "quiz.Answer"

    question = factory.SubFactory(QuestionFactory, answers=[])
    answer = factory.Faker("sentence", nb_words=20, variable_nb_words=True)


class QuizParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "quiz.QuizParticipant"

    quiz = factory.SubFactory(QuizFactory)
    user = factory.SubFactory(UserFactory)


class QuizInvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "quiz.QuizInvitation"

    quiz = factory.SubFactory(QuizFactory)
    email = factory.Faker("email")
    key = factory.Faker("word")
