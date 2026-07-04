import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/helpers.dart';

class ProgressScreen extends StatefulWidget {
  const ProgressScreen({super.key});

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> with SingleTickerProviderStateMixin {
  late TabController _tabs;
  Map<String, dynamic>? _progress;
  Map<String, dynamic>? _plan;
  List<Map<String, dynamic>> _interventions = [];
  bool _loading = false;
  bool _analyzing = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 4, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        ApiService().getFullProgress().catchError((_) => <String, dynamic>{}),
        ApiService().getStudyPlan(context.read<AuthProvider>().student!.studentId)
            .catchError((_) => <String, dynamic>{}),
        ApiService().getInterventions().catchError((_) => <String, dynamic>{}),
      ]);
      setState(() {
        _progress = results[0];
        _plan = results[1];
        _interventions = ((results[2]['interventions'] ?? results[2]['items'] ?? []) as List)
            .cast<Map<String, dynamic>>();
      });
    } catch (_) {
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _runDabbuAnalysis() async {
    setState(() => _analyzing = true);
    try {
      final result = await ApiService().triggerDabbuAnalysis();
      if (mounted) {
        final severity = result['severity'] as String? ?? 'low';
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('🤖 Dabbu analysis done! Severity: $severity'),
          backgroundColor: severity == 'high' ? Colors.red : AppTheme.successColor,
        ));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  Future<void> _takeSnapshot() async {
    try {
      await ApiService().takeSnapshot();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ Snapshot saved'), backgroundColor: AppTheme.successColor));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final student = context.watch<AuthProvider>().student!;
    final lang = student.preferredLanguage;

    return Scaffold(
      appBar: AppBar(
        title: Text(lang == 'hi' ? '📊 प्रगति' : '📊 Progress'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
        bottom: TabBar(
          controller: _tabs,
          tabs: [
            Tab(text: lang == 'hi' ? 'अवलोकन' : 'Overview'),
            Tab(text: lang == 'hi' ? 'योजना' : 'Study Plan'),
            Tab(text: lang == 'hi' ? 'Dabbu' : 'Dabbu AI'),
            const Tab(text: 'SM-2'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabs,
              children: [
                _OverviewTab(student: student, progress: _progress, lang: lang, onSnapshot: _takeSnapshot),
                _StudyPlanTab(plan: _plan, lang: lang),
                _DabbuTab(interventions: _interventions, lang: lang, onAnalyze: _runDabbuAnalysis, analyzing: _analyzing),
                _SM2Tab(progress: _progress, lang: lang),
              ],
            ),
    );
  }
}

// ── Overview Tab ─────────────────────────────────────────────────────────────

class _OverviewTab extends StatelessWidget {
  final dynamic student;
  final Map<String, dynamic>? progress;
  final String lang;
  final VoidCallback onSnapshot;
  const _OverviewTab({required this.student, required this.progress, required this.lang, required this.onSnapshot});

  @override
  Widget build(BuildContext context) {
    final weakness = student.weaknessMap;
    final currentTopics = (progress?['current_topics'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final sessions = (progress?['recent_sessions'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final calendarDays = (progress?['streak_calendar'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final summary = progress?['summary'] as Map<String, dynamic>?;

    return RefreshIndicator(
      onRefresh: () async {},
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Stats row
          Row(
            children: [
              _StatCard(label: lang == 'hi' ? 'क्रम' : 'Streak',
                  value: '${summary?['streak_days'] ?? student.studyStreakDays}d 🔥'),
              const SizedBox(width: 12),
              _StatCard(label: lang == 'hi' ? 'प्रश्न' : 'Questions', value: '${student.totalQuestionsAttempted}'),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _StatCard(
                label: lang == 'hi' ? 'औसत' : 'Accuracy',
                value: weakness.isEmpty ? 'N/A'
                    : '${(weakness.map((w) => w.scorePct).reduce((a, b) => a + b) / weakness.length * 100).toStringAsFixed(0)}%',
              ),
              const SizedBox(width: 12),
              _StatCard(
                label: lang == 'hi' ? 'महारत' : 'Mastered',
                value: '${weakness.where((w) => w.scorePct >= 0.8).length}/${weakness.length}',
              ),
            ],
          ),

          // Streak heatmap
          if (calendarDays.isNotEmpty) ...[
            const SizedBox(height: 20),
            Text(lang == 'hi' ? '🔥 60-दिन का अध्ययन' : '🔥 60-Day Study Activity',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 10),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: _StreakHeatmap(calendarDays: calendarDays),
              ),
            ),
          ],

          const SizedBox(height: 16),

          // Triple bar chart (Initial / Current / Target@80%)
          if (currentTopics.isNotEmpty) ...[
            Text(lang == 'hi' ? '📊 प्रारंभिक · वर्तमान · लक्ष्य' : '📊 Initial · Current · Target (80%)',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: SizedBox(
                  height: 220,
                  child: _TripleBarChart(topics: currentTopics.take(7).toList()),
                ),
              ),
            ),
            const SizedBox(height: 6),
            // Legend
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _LegendDot(color: Colors.blueGrey.shade300, label: 'Initial'),
                const SizedBox(width: 12),
                _LegendDot(color: AppTheme.primary, label: 'Current'),
                const SizedBox(width: 12),
                _LegendDot(color: Colors.green.shade400, label: 'Target 80%'),
              ],
            ),
          ] else if (weakness.isNotEmpty) ...[
            // Fallback: simple single bar chart when no API data
            Text(lang == 'hi' ? '📊 विषयवार प्रदर्शन' : '📊 Subject Performance',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SizedBox(
                  height: 180,
                  child: BarChart(BarChartData(
                    alignment: BarChartAlignment.spaceAround,
                    barGroups: weakness.asMap().entries.take(8).map((e) {
                      final pct = e.value.scorePct as double;
                      return BarChartGroupData(
                        x: e.key,
                        barRods: [BarChartRodData(
                          toY: pct * 100,
                          color: scoreColor(pct),
                          width: 14,
                          borderRadius: BorderRadius.circular(4),
                        )],
                      );
                    }).toList(),
                    titlesData: FlTitlesData(
                      bottomTitles: AxisTitles(sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (v, _) {
                          final idx = v.toInt();
                          if (idx < weakness.length) {
                            return Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(weakness[idx].topic.split(' ').first,
                                  style: const TextStyle(fontSize: 9)),
                            );
                          }
                          return const SizedBox();
                        },
                      )),
                      leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    ),
                    gridData: FlGridData(show: false),
                    borderData: FlBorderData(show: false),
                    maxY: 100,
                  )),
                ),
              ),
            ),
          ],

          // Weak areas list
          if (weakness.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(lang == 'hi' ? '📉 कमज़ोर विषय' : '📉 Weak Areas',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 6),
            ...weakness.take(5).map((w) => Card(
              child: ListTile(
                dense: true,
                leading: Text(scoreEmoji(w.scorePct), style: const TextStyle(fontSize: 20)),
                title: Text(w.topic),
                subtitle: Text(w.subject, style: const TextStyle(fontSize: 11)),
                trailing: Text('${(w.scorePct * 100).toStringAsFixed(0)}%',
                    style: TextStyle(color: scoreColor(w.scorePct), fontWeight: FontWeight.bold)),
              ),
            )),
          ],

          // Recent sessions
          if (sessions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(lang == 'hi' ? '📋 हाल की गतिविधि' : '📋 Recent Sessions',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 6),
            ...sessions.take(5).map((s) => ListTile(
              dense: true,
              leading: Text(
                s['session_type'] == 'mock' || s['type'] == 'mock' ? '🧪'
                    : s['session_type'] == 'practice' || s['type'] == 'practice' ? '✏️' : '📖',
                style: const TextStyle(fontSize: 18),
              ),
              title: Text(s['topic'] as String? ?? s['subject'] as String? ?? '',
                  style: const TextStyle(fontSize: 13)),
              subtitle: Text(s['subject'] as String? ?? '', style: const TextStyle(fontSize: 11)),
              trailing: Text('${s['correct'] ?? 0}/${(s['total'] ?? 1)}',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
            )),
          ],

          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: onSnapshot,
            icon: const Icon(Icons.camera_alt_outlined),
            label: Text(lang == 'hi' ? 'स्नैपशॉट सहेजें' : 'Save Progress Snapshot'),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

// ── Study Plan Tab ────────────────────────────────────────────────────────────

class _StudyPlanTab extends StatelessWidget {
  final Map<String, dynamic>? plan;
  final String lang;
  const _StudyPlanTab({required this.plan, required this.lang});

  @override
  Widget build(BuildContext context) {
    if (plan == null || (plan!['plan'] as List?)?.isEmpty != false) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('📅', style: TextStyle(fontSize: 48)),
            const SizedBox(height: 12),
            Text(
              lang == 'hi'
                  ? 'कोई अध्ययन योजना नहीं\nडायग्नोस्टिक टेस्ट दें और Dabbu आपकी योजना बनाएगा'
                  : 'No study plan yet.\nComplete the diagnostic test and\nDabbu will create your plan.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey, fontSize: 14, height: 1.5),
            ),
          ],
        ),
      );
    }

    final days = (plan!['plan'] as List).cast<Map<String, dynamic>>();
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        if (plan!['exam_target'] != null)
          Chip(
            label: Text('${plan!['exam_target']} — ${days.length} day plan',
                style: const TextStyle(fontSize: 12)),
            backgroundColor: AppTheme.primary.withOpacity(0.1),
          ),
        const SizedBox(height: 8),
        ...days.map((day) {
          final sessions = (day['sessions'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ExpansionTile(
              leading: CircleAvatar(
                radius: 18,
                backgroundColor: AppTheme.primary.withOpacity(0.1),
                child: Text('D${day['day']}',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary, fontSize: 12)),
              ),
              title: Text(day['date'] as String? ?? '', style: const TextStyle(fontSize: 13)),
              subtitle: Text('${sessions.length} ${lang == 'hi' ? 'सत्र' : 'sessions'}',
                  style: const TextStyle(fontSize: 11)),
              children: sessions.map((s) => ListTile(
                dense: true,
                leading: Text(
                  s['type'] == 'study' ? '📖' : s['type'] == 'practice' ? '✏️' : '🔄',
                  style: const TextStyle(fontSize: 16),
                ),
                title: Text(s['topic'] as String? ?? '', style: const TextStyle(fontSize: 13)),
                trailing: Text(formatDuration((s['duration_minutes'] as num?)?.toInt() ?? 30),
                    style: const TextStyle(fontSize: 11, color: Colors.grey)),
              )).toList(),
            ),
          );
        }),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () async {
            try {
              final student = context.read<AuthProvider>().student!;
              final result = await ApiService().createSchedule(student.studentId);
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                content: Text('✅ ${result['count']} calendar events created!'),
                backgroundColor: AppTheme.successColor,
              ));
            } catch (e) {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
            }
          },
          icon: const Icon(Icons.calendar_month),
          label: Text(lang == 'hi' ? 'कैलेंडर इवेंट बनाएं' : 'Add to Calendar'),
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}

// ── Dabbu Tab ─────────────────────────────────────────────────────────────────

class _DabbuTab extends StatelessWidget {
  final List<Map<String, dynamic>> interventions;
  final String lang;
  final VoidCallback onAnalyze;
  final bool analyzing;
  const _DabbuTab({
    required this.interventions,
    required this.lang,
    required this.onAnalyze,
    required this.analyzing,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Dabbu header
        Card(
          color: AppTheme.primary.withOpacity(0.06),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Text('🤖', style: TextStyle(fontSize: 36)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Dabbu AI Agent',
                          style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                      Text(
                        lang == 'hi'
                            ? 'Dabbu आपकी कमज़ोरियों का विश्लेषण करता है और NAGA की मंज़ूरी के बाद योजना बनाता है।'
                            : 'Dabbu analyzes your progress and proposes plans — NAGA reviews before you see them.',
                        style: const TextStyle(fontSize: 12, color: Colors.grey, height: 1.4),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: analyzing ? null : onAnalyze,
            icon: analyzing
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Icon(Icons.psychology),
            label: Text(lang == 'hi' ? 'Dabbu से विश्लेषण करवाएं' : 'Ask Dabbu to Analyze My Progress'),
          ),
        ),
        const SizedBox(height: 20),
        Text(lang == 'hi' ? '📋 Dabbu सुझाव' : '📋 Dabbu Interventions',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 8),
        if (interventions.isEmpty)
          Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                lang == 'hi'
                    ? 'कोई सुझाव नहीं। Dabbu से विश्लेषण करवाएं।'
                    : 'No interventions yet.\nTap "Ask Dabbu to Analyze" above.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey, height: 1.5),
              ),
            ),
          )
        else
          ...interventions.map((inv) => _InterventionCard(inv: inv, lang: lang)),
        const SizedBox(height: 24),
      ],
    );
  }
}

class _InterventionCard extends StatelessWidget {
  final Map<String, dynamic> inv;
  final String lang;
  const _InterventionCard({required this.inv, required this.lang});

  @override
  Widget build(BuildContext context) {
    final severity = inv['severity'] as String? ?? 'low';
    final severityColor = severity == 'high' ? Colors.red : severity == 'medium' ? Colors.orange : Colors.blue;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('🤖', style: TextStyle(fontSize: 16)),
                const SizedBox(width: 6),
                Text('Dabbu', style: TextStyle(fontWeight: FontWeight.w700, color: AppTheme.primary)),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: severityColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(severity.toUpperCase(),
                      style: TextStyle(fontSize: 10, color: severityColor, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(inv['message'] as String? ?? inv['recommendation'] as String? ?? '',
                style: const TextStyle(fontSize: 13, height: 1.4)),
            if ((inv['flags'] as List?)?.isNotEmpty == true) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                children: ((inv['flags'] as List).cast<String>()).map((f) => Chip(
                  label: Text(f, style: const TextStyle(fontSize: 10)),
                  backgroundColor: Colors.orange.withOpacity(0.1),
                  padding: EdgeInsets.zero,
                )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ── Shared widgets ────────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  final String label, value;
  const _StatCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          child: Column(
            children: [
              Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppTheme.primary)),
              Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Streak Heatmap ────────────────────────────────────────────────────────────

class _StreakHeatmap extends StatelessWidget {
  final List<Map<String, dynamic>> calendarDays;
  const _StreakHeatmap({required this.calendarDays});

  Color _cellColor(int count) {
    if (count == 0) return Colors.grey.shade100;
    if (count == 1) return AppTheme.primary.withOpacity(0.25);
    if (count <= 3) return AppTheme.primary.withOpacity(0.55);
    return AppTheme.primary;
  }

  @override
  Widget build(BuildContext context) {
    // Build weeks (7 days each)
    final weeks = <List<Map<String, dynamic>>>[];
    var week = <Map<String, dynamic>>[];
    for (final day in calendarDays) {
      week.add(day);
      if (week.length == 7) { weeks.add(List.from(week)); week = []; }
    }
    if (week.isNotEmpty) weeks.add(week);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: weeks.map((wk) => Padding(
              padding: const EdgeInsets.only(right: 3),
              child: Column(
                children: wk.map((day) {
                  final count = (day['count'] as num?)?.toInt() ?? 0;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 3),
                    child: Tooltip(
                      message: '${day['date']}: $count session${count != 1 ? 's' : ''}',
                      child: Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(
                          color: _cellColor(count),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            )).toList(),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Text('Less', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
            const SizedBox(width: 4),
            ...([0, 1, 2, 4]).map((c) => Padding(
              padding: const EdgeInsets.only(right: 3),
              child: Container(
                width: 10, height: 10,
                decoration: BoxDecoration(
                  color: _cellColor(c),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            )),
            Text('More', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
          ],
        ),
      ],
    );
  }
}

// ── Triple Bar Chart (Initial / Current / Target) ─────────────────────────────

class _TripleBarChart extends StatelessWidget {
  final List<Map<String, dynamic>> topics;
  const _TripleBarChart({required this.topics});

  @override
  Widget build(BuildContext context) {
    const double barWidth = 6;
    const double groupSpace = 6;

    final groups = topics.asMap().entries.map((e) {
      final t = e.value;
      final initial = ((t['initial_score_pct'] as num?)?.toDouble() ?? 0.0) * 100;
      final current = ((t['score_pct'] as num?)?.toDouble() ?? 0.0) * 100;
      const target = 80.0;
      return BarChartGroupData(
        x: e.key,
        groupVertically: false,
        barsSpace: 2,
        barRods: [
          BarChartRodData(
            toY: initial,
            color: Colors.blueGrey.shade300,
            width: barWidth,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
          ),
          BarChartRodData(
            toY: current,
            color: AppTheme.primary,
            width: barWidth,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
          ),
          BarChartRodData(
            toY: target,
            color: Colors.green.shade400.withOpacity(0.5),
            width: barWidth,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
          ),
        ],
      );
    }).toList();

    return BarChart(BarChartData(
      alignment: BarChartAlignment.spaceAround,
      groupsSpace: groupSpace,
      barGroups: groups,
      titlesData: FlTitlesData(
        bottomTitles: AxisTitles(sideTitles: SideTitles(
          showTitles: true,
          reservedSize: 32,
          getTitlesWidget: (v, _) {
            final idx = v.toInt();
            if (idx < topics.length) {
              final name = (topics[idx]['topic'] as String? ?? '');
              final label = name.length > 8 ? '${name.substring(0, 7)}…' : name;
              return Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(label, style: const TextStyle(fontSize: 8)),
              );
            }
            return const SizedBox();
          },
        )),
        leftTitles: AxisTitles(sideTitles: SideTitles(
          showTitles: true,
          reservedSize: 28,
          getTitlesWidget: (v, _) => Text('${v.toInt()}', style: const TextStyle(fontSize: 9)),
        )),
        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: 20,
        getDrawingHorizontalLine: (_) => FlLine(color: Colors.grey.shade200, strokeWidth: 1),
      ),
      borderData: FlBorderData(show: false),
      maxY: 100,
    ));
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
      ],
    );
  }
}

// ── SM-2 Tab ──────────────────────────────────────────────────────────────────

class _SM2Tab extends StatelessWidget {
  final Map<String, dynamic>? progress;
  final String lang;
  const _SM2Tab({required this.progress, required this.lang});

  @override
  Widget build(BuildContext context) {
    final topics = (progress?['current_topics'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final summary = progress?['summary'] as Map<String, dynamic>?;
    final overdueCount = (summary?['overdue_reviews'] as num?)?.toInt() ?? 0;

    if (topics.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('🧠', style: TextStyle(fontSize: 48)),
              const SizedBox(height: 12),
              Text(
                lang == 'hi'
                    ? 'SM-2 डेटा उपलब्ध नहीं है।\nडायग्नोस्टिक या प्रैक्टिस टेस्ट दें।'
                    : 'No SM-2 data yet.\nComplete a diagnostic or practice session.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey, fontSize: 14, height: 1.5),
              ),
            ],
          ),
        ),
      );
    }

    // Sort: overdue first, then by days_until_review ascending
    final sorted = List<Map<String, dynamic>>.from(topics)
      ..sort((a, b) {
        final aOverdue = a['overdue'] == true;
        final bOverdue = b['overdue'] == true;
        if (aOverdue && !bOverdue) return -1;
        if (!aOverdue && bOverdue) return 1;
        final aDays = (a['days_until_review'] as num?)?.toInt() ?? 0;
        final bDays = (b['days_until_review'] as num?)?.toInt() ?? 0;
        return aDays.compareTo(bDays);
      });

    return ListView(
      padding: const EdgeInsets.all(14),
      children: [
        // Header summary
        if (overdueCount > 0)
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.red.shade50,
              border: Border.all(color: Colors.red.shade200),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 18),
                const SizedBox(width: 8),
                Text(
                  '$overdueCount ${lang == 'hi' ? 'समीक्षाएं बाकी हैं' : 'review${overdueCount > 1 ? 's' : ''} overdue'}',
                  style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w700, fontSize: 13),
                ),
              ],
            ),
          ),
        // Legend
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text(
            lang == 'hi' ? 'SM-2 स्पेस्ड रिपेटीशन समीक्षा शेड्यूल' : 'SM-2 Spaced Repetition Review Schedule',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
        ),
        ...sorted.map((t) => _SM2Card(topic: t)),
        const SizedBox(height: 24),
      ],
    );
  }
}

class _SM2Card extends StatelessWidget {
  final Map<String, dynamic> topic;
  const _SM2Card({required this.topic});

  Color _easeColor(String? label) {
    switch (label) {
      case 'Hard': return Colors.red;
      case 'Moderate': return Colors.orange;
      case 'Good': return Colors.blue;
      default: return Colors.green;
    }
  }

  @override
  Widget build(BuildContext context) {
    final overdue = topic['overdue'] == true;
    final daysUntil = (topic['days_until_review'] as num?)?.toInt() ?? 0;
    final easeFactor = (topic['ease_factor'] as num?)?.toDouble() ?? 2.5;
    final intervalDays = (topic['interval_days'] as num?)?.toInt() ?? 1;
    final nextReview = topic['next_review_date'] as String? ?? '';
    final easeLabel = topic['ease_label'] as String? ?? 'Good';

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      color: overdue ? Colors.red.shade50 : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: overdue ? Colors.red.shade200 : Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(topic['topic'] as String? ?? '',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                      Text(topic['subject'] as String? ?? '',
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                    ],
                  ),
                ),
                if (overdue)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: Colors.red.shade100,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text('OVERDUE ${daysUntil.abs()}d',
                        style: const TextStyle(fontSize: 10, color: Colors.red, fontWeight: FontWeight.bold)),
                  )
                else
                  Text('in ${daysUntil}d', style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                _SM2Stat(label: 'Ease', value: easeLabel,
                    valueColor: _easeColor(easeLabel),
                    sub: easeFactor.toStringAsFixed(2)),
                const SizedBox(width: 16),
                _SM2Stat(label: 'Interval', value: '${intervalDays}d', valueColor: AppTheme.primary),
                const SizedBox(width: 16),
                _SM2Stat(label: 'Next Review',
                    value: nextReview.length > 5 ? nextReview.substring(5) : nextReview,
                    valueColor: overdue ? Colors.red : Colors.grey.shade800),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SM2Stat extends StatelessWidget {
  final String label, value;
  final Color valueColor;
  final String? sub;
  const _SM2Stat({required this.label, required this.value, required this.valueColor, this.sub});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
        Text(value, style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: valueColor)),
        if (sub != null) Text(sub!, style: TextStyle(fontSize: 9, color: Colors.grey.shade400)),
      ],
    );
  }
}
