class Question {
  final String questionId;
  final String subject;
  final String topic;
  final int difficulty;
  final int correctIndex;
  final String questionTextEn;
  final String? questionTextHi;
  final List<String> options;
  final String explanationEn;
  final String? explanationHi;

  const Question({
    required this.questionId,
    required this.subject,
    required this.topic,
    required this.difficulty,
    required this.correctIndex,
    required this.questionTextEn,
    this.questionTextHi,
    required this.options,
    required this.explanationEn,
    this.explanationHi,
  });

  factory Question.fromJson(Map<String, dynamic> json) {
    return Question(
      questionId: json['question_id'] as String,
      subject: json['subject'] as String,
      topic: json['topic'] as String,
      difficulty: (json['difficulty'] as num).toInt(),
      correctIndex: (json['correct_index'] as num).toInt(),
      questionTextEn: json['question_text_en'] as String,
      questionTextHi: json['question_text_hi'] as String?,
      options: List<String>.from(json['options'] as List),
      explanationEn: json['explanation_en'] as String,
      explanationHi: json['explanation_hi'] as String?,
    );
  }

  String textFor(String lang) =>
    (lang == 'hi' && questionTextHi != null) ? questionTextHi! : questionTextEn;

  String explanationFor(String lang) =>
    (lang == 'hi' && explanationHi != null) ? explanationHi! : explanationEn;
}
