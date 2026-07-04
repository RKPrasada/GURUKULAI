import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../theme/app_theme.dart';

/// A2UI dispatcher — reads _card_type from the API response dict
/// and renders the appropriate card widget.
class CardRenderer extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;

  const CardRenderer({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final cardType = result['_card_type'] as String? ?? '';
    return switch (cardType) {
      'note_card'       => NoteCard(result: result, lang: lang),
      'quiz_card'       => QuizCard(result: result, lang: lang),
      'quiz_result_card' => QuizResultCard(result: result, lang: lang),
      'diagnostic_card' => DiagnosticCard(result: result, lang: lang),
      'diag_result_card' => DiagResultCard(result: result, lang: lang),
      'plan_card'       => PlanCard(result: result, lang: lang),
      'feedback_card'   => FeedbackCard(result: result, lang: lang),
      'alert_card'      => AlertCard(result: result, lang: lang),
      'vibe_diff_card'  => VibeDiffCard(result: result, lang: lang),
      _                 => _GenericCard(result: result),
    };
  }
}

// ─── NoteCard ────────────────────────────────────────────────────────────────

class NoteCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const NoteCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final topic = result['topic'] as String? ?? '';
    final notes = result['notes'] as String? ?? '';
    final driveUrl = result['drive_url'] as String?;
    final videos = (result['youtube_videos'] as List?)?.cast<Map<String, dynamic>>() ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (topic.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text('📖 $topic',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: AppTheme.primary, fontWeight: FontWeight.w700)),
          ),
        if (notes.isNotEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: MarkdownBody(data: notes, shrinkWrap: true),
            ),
          ),
        if (driveUrl != null)
          _StatusChip(
            icon: Icons.cloud_done,
            color: Colors.green,
            label: lang == 'hi' ? 'Drive में सहेजा गया' : 'Saved to Drive',
          ),
        if (videos.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(lang == 'hi' ? '🎬 वीडियो संसाधन' : '🎬 Video Resources',
              style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ...videos.map((v) => _VideoTile(video: v)),
        ],
      ],
    );
  }
}

// ─── QuizCard ────────────────────────────────────────────────────────────────

class QuizCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const QuizCard({super.key, required this.result, required this.lang});

  static const _diffLabel = {1: '🟢 Easy', 2: '🟡 Medium', 3: '🔴 Hard'};

  @override
  Widget build(BuildContext context) {
    final difficulty = result['difficulty'] as int? ?? 1;
    final total = result['total'] as int? ?? 0;
    final q = result['first_question'] as Map<String, dynamic>?;
    final qText = (lang == 'hi' ? (q != null ? q['question_text_hi'] : null) : null) ??
        (q != null ? q['question_text_en'] : null) ?? '';
    final options = (q?['options'] as List?)?.cast<String>() ?? [];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Text('📝 ', style: TextStyle(fontSize: 18)),
              Text(lang == 'hi' ? 'अभ्यास प्रश्नोत्तरी' : 'Practice Quiz',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              const Spacer(),
              _Chip(label: _diffLabel[difficulty] ?? '', color: AppTheme.secondary),
              const SizedBox(width: 8),
              _Chip(label: '$total Qs', color: Colors.grey.shade400),
            ]),
            const Divider(height: 24),
            if (qText.isNotEmpty) ...[
              Text('Q1: $qText', style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 12),
              ...options.asMap().entries.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text('${String.fromCharCode(65 + e.key)}. ${e.value}'),
              )),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── QuizResultCard ──────────────────────────────────────────────────────────

class QuizResultCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const QuizResultCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final correct = result['correct'] as bool? ?? false;
    final score = result['score'] as int? ?? 0;
    final answered = result['answered'] as int? ?? 0;
    final total = result['total'] as int? ?? 1;
    final explanation = (lang == 'hi' ? result['explanation_hi'] : null) ??
        result['explanation_en'] ?? '';
    final complete = result['session_complete'] as bool? ?? false;

    return Card(
      color: correct ? const Color(0xFFE8F5E9) : const Color(0xFFFFEBEE),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(correct
                ? (lang == 'hi' ? '✅ सही!' : '✅ Correct!')
                : (lang == 'hi' ? '❌ गलत।' : '❌ Not quite.'),
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: correct ? Colors.green.shade800 : Colors.red.shade800)),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: answered / total,
              color: correct ? Colors.green : Colors.red,
              backgroundColor: Colors.grey.shade200,
              minHeight: 6,
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Text('${lang == 'hi' ? 'अंक' : 'Score'}: $score / $total',
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ),
            if (explanation.isNotEmpty) ...[
              const SizedBox(height: 8),
              ExpansionTile(
                title: Text(lang == 'hi' ? 'स्पष्टीकरण' : 'Explanation'),
                initiallyExpanded: !correct,
                children: [
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: MarkdownBody(data: explanation, shrinkWrap: true),
                  ),
                ],
              ),
            ],
            if (complete)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text('🎉 Session complete!',
                    style: TextStyle(fontWeight: FontWeight.w700, color: Colors.teal)),
              ),
          ],
        ),
      ),
    );
  }
}

// ─── DiagnosticCard ──────────────────────────────────────────────────────────

class DiagnosticCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const DiagnosticCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final total = result['total'] as int? ?? 0;
    final questions = (result['questions'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final q = questions.isNotEmpty ? questions[0] : null;
    final qText = (lang == 'hi' ? (q != null ? q['question_text_hi'] : null) : null) ??
        (q != null ? q['question_text_en'] : null) ?? '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(lang == 'hi' ? '📋 निदान परीक्षण' : '📋 Diagnostic Assessment',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 4),
            Text('$total questions', style: const TextStyle(color: Colors.grey)),
            const Divider(height: 20),
            if (qText.isNotEmpty)
              Text('Q1: $qText', style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

// ─── DiagResultCard ──────────────────────────────────────────────────────────

class DiagResultCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const DiagResultCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final scorePct = ((result['score_pct'] as num?)?.toDouble() ?? 0) * 100;
    final totalC = result['total_correct'] as int? ?? 0;
    final totalQ = result['total_questions'] as int? ?? 0;
    final summary = result['summary'] as String? ?? '';
    final weakness = (result['weakness_map'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    weakness.sort((a, b) =>
        ((a['score_pct'] as num?) ?? 0).compareTo((b['score_pct'] as num?) ?? 0));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(lang == 'hi' ? '📊 निदान परिणाम' : '📊 Diagnostic Results',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 12),
            Row(children: [
              _MetricChip(label: '${scorePct.toStringAsFixed(0)}%', sublabel: 'Score'),
              const SizedBox(width: 12),
              _MetricChip(label: '$totalC/$totalQ', sublabel: 'Correct'),
            ]),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(summary),
              ),
            ],
            if (weakness.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(lang == 'hi' ? 'ध्यान देने वाले विषय:' : 'Focus areas:',
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              ...weakness.take(5).map((w) {
                final pct = ((w['score_pct'] as num?)?.toDouble() ?? 0) * 100;
                final dot = pct < 40 ? '🔴' : pct < 70 ? '🟡' : '🟢';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('$dot ${w['subject']} → ${w['topic']} (${pct.toStringAsFixed(0)}%)'),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── PlanCard ─────────────────────────────────────────────────────────────────

class PlanCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const PlanCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final planData = result['plan'] as Map<String, dynamic>?;
    final days = (planData?['plan'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final totalHours = (planData?['total_hours'] as num?)?.toDouble() ?? 0;
    final weakCovered = (planData?['weak_topics_covered'] as List?) ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(lang == 'hi' ? '📅 7-दिवसीय अध्ययन योजना' : '📅 7-Day Study Plan',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        const SizedBox(height: 8),
        Row(children: [
          _MetricChip(label: '${totalHours}h', sublabel: 'Total'),
          const SizedBox(width: 12),
          _MetricChip(label: '${weakCovered.length}', sublabel: 'Weak topics'),
        ]),
        const SizedBox(height: 12),
        ...days.take(7).map((day) => _DayTile(day: day, lang: lang)),
      ],
    );
  }
}

class _DayTile extends StatelessWidget {
  final Map<String, dynamic> day;
  final String lang;
  const _DayTile({required this.day, required this.lang});

  @override
  Widget build(BuildContext context) {
    final sessions = (day['sessions'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final typeIcon = {'study': '📖', 'practice': '✏️', 'revision': '🔁'};
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ExpansionTile(
        title: Text('Day ${day['day']} — ${day['date']}',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        children: sessions.map((s) => ListTile(
          leading: Text(typeIcon[s['type']] ?? '📌'),
          title: Text(s['topic'] as String? ?? ''),
          subtitle: Text('${s['time']}  ·  ${s['duration_minutes']} min'),
          dense: true,
        )).toList(),
      ),
    );
  }
}

// ─── FeedbackCard ─────────────────────────────────────────────────────────────

class FeedbackCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const FeedbackCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final explanation = result['explanation'] as String? ?? '';
    final concept = result['concept'] as String? ?? '';
    final encouragement = result['encouragement'] as String? ?? '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(lang == 'hi' ? '💡 स्पष्टीकरण' : '💡 Explanation',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 12),
            if (explanation.isNotEmpty) MarkdownBody(data: explanation, shrinkWrap: true),
            if (concept.isNotEmpty) ...[
              const SizedBox(height: 12),
              _StatusChip(
                icon: Icons.lightbulb_outline,
                color: Colors.amber,
                label: '${lang == 'hi' ? 'मुख्य अवधारणा' : 'Key concept'}: $concept',
              ),
            ],
            if (encouragement.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(encouragement,
                    style: TextStyle(color: Colors.green.shade800)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── AlertCard ────────────────────────────────────────────────────────────────

class AlertCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;
  const AlertCard({super.key, required this.result, required this.lang});

  @override
  Widget build(BuildContext context) {
    final message = result['response'] as String? ?? '';
    return Card(
      color: Colors.orange.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.orange.shade700),
            const SizedBox(width: 12),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    );
  }
}

// ─── VibeDiffCard ─────────────────────────────────────────────────────────────

class VibeDiffCard extends StatelessWidget {
  final Map<String, dynamic> result;
  final String lang;

  const VibeDiffCard({super.key, required this.result, required this.lang});

  static const _riskIcon = {
    'low': '🟢', 'medium': '🟡', 'high': '🔴', 'critical': '🚨'
  };

  @override
  Widget build(BuildContext context) {
    final pending = result['pending_action'] as Map<String, dynamic>? ?? {};
    final desc = pending['description'] as String? ?? result['message'] as String? ?? '';
    final risk = pending['risk_level'] as String? ?? 'medium';
    final token = pending['token'] as String? ?? '';
    final riskIcon = _riskIcon[risk] ?? '🟡';

    return Card(
      color: Colors.amber.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(lang == 'hi' ? '🔐 कार्रवाई की पुष्टि करें' : '🔐 Confirm Action',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 8),
            Text('$riskIcon Risk: ${risk.toUpperCase()}',
                style: TextStyle(color: Colors.orange.shade800, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text(desc),
            if (token.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Text(token,
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
              ),
              const SizedBox(height: 4),
              Text(
                lang == 'hi' ? 'पुष्टि टोकन — ऊपर "पुष्टि करें" दबाएं'
                              : 'Confirmation token — tap Confirm above',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── Generic fallback ─────────────────────────────────────────────────────────

class _GenericCard extends StatelessWidget {
  final Map<String, dynamic> result;
  const _GenericCard({required this.result});

  @override
  Widget build(BuildContext context) {
    final text = result['notes'] as String? ??
        result['response'] as String? ??
        result['message'] as String? ??
        result['summary'] as String? ?? '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: text.isNotEmpty
            ? MarkdownBody(data: text, shrinkWrap: true)
            : Text(result.toString()),
      ),
    );
  }
}

// ─── Shared helper widgets ────────────────────────────────────────────────────

class _StatusChip extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  const _StatusChip({required this.icon, required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 6),
        Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final Color color;
  const _Chip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
    );
  }
}

class _MetricChip extends StatelessWidget {
  final String label;
  final String sublabel;
  const _MetricChip({required this.label, required this.sublabel});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppTheme.primary)),
        Text(sublabel, style: const TextStyle(fontSize: 11, color: Colors.grey)),
      ],
    );
  }
}

class _VideoTile extends StatelessWidget {
  final Map<String, dynamic> video;
  const _VideoTile({required this.video});

  @override
  Widget build(BuildContext context) {
    final title = video['title'] as String? ?? '';
    final url = video['url'] as String? ?? '';
    final channel = video['channel'] as String? ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 6),
      child: ListTile(
        leading: const Text('🎬', style: TextStyle(fontSize: 20)),
        title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: channel.isNotEmpty ? Text(channel) : null,
        trailing: const Icon(Icons.open_in_new, size: 16),
        onTap: () async {
          if (url.isNotEmpty) {
            final uri = Uri.parse(url);
            if (await canLaunchUrl(uri)) await launchUrl(uri);
          }
        },
      ),
    );
  }
}
