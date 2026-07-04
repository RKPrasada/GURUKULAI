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

class _ProgressScreenState extends State<ProgressScreen> {
  Map<String, dynamic>? _plan;
  bool _loadingPlan = false;
  String? _digestEmail;
  bool _sendingDigest = false;

  @override
  void initState() {
    super.initState();
    _loadPlan();
  }

  Future<void> _loadPlan() async {
    final student = context.read<AuthProvider>().student!;
    setState(() => _loadingPlan = true);
    try {
      _plan = await ApiService().getStudyPlan(student.studentId);
    } catch (_) {} finally {
      setState(() => _loadingPlan = false);
    }
  }

  Future<void> _createEvents() async {
    final student = context.read<AuthProvider>().student!;
    try {
      final result = await ApiService().createSchedule(student.studentId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('✅ ${result['count']} calendar events created!'),
          backgroundColor: AppTheme.successColor,
        ));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  Future<void> _sendDigest() async {
    if (_digestEmail == null || _digestEmail!.isEmpty) return;
    final student = context.read<AuthProvider>().student!;
    setState(() => _sendingDigest = true);
    try {
      await ApiService().sendDigest(student.studentId, _digestEmail!, 'Student');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('✅ Report sent to $_digestEmail!'),
          backgroundColor: AppTheme.successColor,
        ));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() => _sendingDigest = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final student = context.watch<AuthProvider>().student!;
    final lang = student.preferredLanguage;
    final weakness = student.weaknessMap;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Stats row
        Row(
          children: [
            _StatCard(label: lang == 'hi' ? 'क्रम' : 'Streak', value: '${student.studyStreakDays}d 🔥'),
            const SizedBox(width: 12),
            _StatCard(label: lang == 'hi' ? 'प्रश्न' : 'Questions', value: '${student.totalQuestionsAttempted}'),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            _StatCard(
              label: lang == 'hi' ? 'औसत' : 'Accuracy',
              value: weakness.isEmpty ? 'N/A' : '${(weakness.map((w) => w.scorePct).reduce((a,b)=>a+b)/weakness.length*100).toStringAsFixed(0)}%',
            ),
            const SizedBox(width: 12),
            _StatCard(
              label: lang == 'hi' ? 'महारत' : 'Mastered',
              value: '${weakness.where((w) => w.scorePct >= 0.8).length}',
            ),
          ],
        ),

        const SizedBox(height: 16),

        // Subject chart
        if (weakness.isNotEmpty) ...[
          Text(lang == 'hi' ? '📊 विषयवार प्रदर्शन' : '📊 Subject Performance',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                height: 180,
                child: BarChart(
                  BarChartData(
                    alignment: BarChartAlignment.spaceAround,
                    barGroups: weakness.asMap().entries.map((e) {
                      final pct = e.value.scorePct;
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
                                  style: const TextStyle(fontSize: 9), overflow: TextOverflow.ellipsis),
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
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],

        // 7-day plan
        Text(lang == 'hi' ? '📅 7-दिन की योजना' : '📅 7-Day Study Plan',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        const SizedBox(height: 8),
        if (_loadingPlan)
          const Center(child: CircularProgressIndicator())
        else if (_plan != null) ...[
          ...(_plan!['plan'] as List? ?? []).map((day) {
            final d = day as Map<String, dynamic>;
            final sessions = (d['sessions'] as List? ?? []).cast<Map<String, dynamic>>();
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ExpansionTile(
                leading: CircleAvatar(
                  backgroundColor: AppTheme.primary.withOpacity(0.1),
                  child: Text('D${d['day']}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary, fontSize: 12)),
                ),
                title: Text('${d['date']}'),
                subtitle: Text('${sessions.length} sessions'),
                children: sessions.map((s) => ListTile(
                  leading: Text(s['type'] == 'study' ? '📖' : s['type'] == 'practice' ? '✏️' : '🔄'),
                  title: Text(s['topic'] as String? ?? ''),
                  trailing: Text(formatDuration((s['duration_minutes'] as num).toInt())),
                )).toList(),
              ),
            );
          }),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _createEvents,
            icon: const Icon(Icons.calendar_month),
            label: Text(lang == 'hi' ? 'कैलेंडर इवेंट बनाएं' : 'Create Calendar Events'),
          ),
        ],

        const SizedBox(height: 16),

        // Weekly digest
        Text(lang == 'hi' ? '📧 साप्ताहिक रिपोर्ट' : '📧 Weekly Digest',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        const SizedBox(height: 8),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(
                  onChanged: (v) => _digestEmail = v,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    hintText: lang == 'hi' ? 'आपका ईमेल पता' : 'Your email address',
                    prefixIcon: const Icon(Icons.email_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _sendingDigest ? null : _sendDigest,
                    child: _sendingDigest
                        ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Text(lang == 'hi' ? '📨 रिपोर्ट भेजें' : '📨 Send Report'),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}

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
