
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db import connection
from codeferJudge.settings import BASE_URL

from user.models import Submission
from problem.constants import Judge

from .judges import judge_gcc, judge_gpp, judge_python
from .models import Problem, TestCase
import threading


@login_required(login_url='login_n')
def problem(request, prob_id):
    problem = Problem.objects.get(id=prob_id)

    if request.method == 'POST':
        submission = Submission(user=request.user,
                                problem=problem,
                                code=request.POST['code'],
                                judge=request.POST['language'])
        testcases = list(submission.problem.testcase_set.all())
        submission.save()
        t = threading.Thread(target=run_testcases,
                             args=(submission, testcases,))
        t.start()
        return redirect('submissions')

    latest_submission = Submission.objects.filter(
        user=request.user, problem=problem).order_by('-datetime').first()

    submission_id = request.GET.get('submission_id', None)
    code = ''
    judge = ''
    print('sub_id', submission_id)

    if(submission_id):
        submission = Submission.objects.get(id=submission_id)
        code = submission.code
        judge = submission.judge
    elif latest_submission:
        code = latest_submission.code
        judge = latest_submission.judge

    print('testcase', TestCase.objects.filter(
        problem_id=problem.id, is_sample=True).first())
    "replcae sample tescases \n"
    sample_testCases = TestCase.objects.filter(problem_id=problem.id, is_sample=True)
    for tst_case in sample_testCases:
        tst_case.input = tst_case.input.replace('\\n','\n')
        tst_case.output = tst_case.output.replace('\\n','\n')
    context = {
        'problem': problem,
        'samples': sample_testCases,
        'judges': Submission.JUDGE_CHOICES,
        'precode': code,
        'prejudge': judge,
        'BASE_URL': BASE_URL,
    }
    return render(request, 'problem.html', context)


def run_testcases(sub: Submission, testcases):

    if sub.judge == Judge.PY2:
        output = judge_python(sub, testcases, False)
    elif sub.judge == Judge.PY3:
        output = judge_python(sub, testcases, True)
    elif sub.judge == Judge.GCC:
        output = judge_gcc(sub, testcases)
    elif sub.judge == Judge.GPP14:
        output = judge_gpp(sub, testcases, 14)

    sub.verdict = output['verdict']
    sub.time = output['time']
    connection.close()
    sub.save()
