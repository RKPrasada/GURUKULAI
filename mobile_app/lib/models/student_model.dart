class WeaknessMap {
  final String subject;
  final String topic;
  final double scorePct;
  final int attempts;

  const WeaknessMap({
    required this.subject,
    required this.topic,
    required this.scorePct,
    required this.attempts,
  });

  factory WeaknessMap.fromJson(Map<String, dynamic> json) {
    return WeaknessMap(
      subject: json['subject'] as String,
      topic: json['topic'] as String,
      scorePct: (json['score_pct'] as num).toDouble(),
      attempts: (json['attempts'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
    'subject': subject,
    'topic': topic,
    'score_pct': scorePct,
    'attempts': attempts,
  };
}

class StudentProfile {
  final String studentId;
  final String examTarget;
  final String preferredLanguage;
  final bool diagnosticDone;
  final List<WeaknessMap> weaknessMap;
  final int studyStreakDays;
  final int totalQuestionsAttempted;
  final String? name;
  final String? username;
  final String? email;

  const StudentProfile({
    required this.studentId,
    required this.examTarget,
    required this.preferredLanguage,
    required this.diagnosticDone,
    required this.weaknessMap,
    required this.studyStreakDays,
    required this.totalQuestionsAttempted,
    this.name,
    this.username,
    this.email,
  });

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    // API may return user_id (auth login) or student_id (demo/session)
    final id = (json['student_id'] ?? json['user_id'] ?? '') as String;
    return StudentProfile(
      studentId: id,
      examTarget: json['exam_target'] as String,
      preferredLanguage: json['preferred_language'] as String,
      diagnosticDone: json['diagnostic_done'] as bool? ?? false,
      weaknessMap: (json['weakness_map'] as List<dynamic>? ?? [])
          .map((e) => WeaknessMap.fromJson(e as Map<String, dynamic>))
          .toList(),
      studyStreakDays: (json['study_streak_days'] as num?)?.toInt() ?? 0,
      totalQuestionsAttempted: (json['total_questions_attempted'] as num?)?.toInt() ?? 0,
      name: (json['full_name'] ?? json['name']) as String?,
      username: json['username'] as String?,
      email: json['email'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'student_id': studentId,
    'exam_target': examTarget,
    'preferred_language': preferredLanguage,
    'diagnostic_done': diagnosticDone,
    'weakness_map': weaknessMap.map((w) => w.toJson()).toList(),
    'study_streak_days': studyStreakDays,
    'total_questions_attempted': totalQuestionsAttempted,
    if (name != null) 'full_name': name,
    if (username != null) 'username': username,
    if (email != null) 'email': email,
  };

  StudentProfile copyWith({
    bool? diagnosticDone,
    List<WeaknessMap>? weaknessMap,
    String? preferredLanguage,
    int? studyStreakDays,
    int? totalQuestionsAttempted,
    String? name,
    String? username,
    String? email,
  }) {
    return StudentProfile(
      studentId: studentId,
      examTarget: examTarget,
      preferredLanguage: preferredLanguage ?? this.preferredLanguage,
      diagnosticDone: diagnosticDone ?? this.diagnosticDone,
      weaknessMap: weaknessMap ?? this.weaknessMap,
      studyStreakDays: studyStreakDays ?? this.studyStreakDays,
      totalQuestionsAttempted: totalQuestionsAttempted ?? this.totalQuestionsAttempted,
      name: name ?? this.name,
      username: username ?? this.username,
      email: email ?? this.email,
    );
  }

  String get displayName => name ?? username ?? 'Student';
}
