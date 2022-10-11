from zubbi.models import ZuulJob


def test_zuul_job_description():
    job = ZuulJob()
    job.job_name = "foo"
    job.description_html = "<p>Some nice html</p>"

    # Validate that the description is rendered correctly and doesn't
    # result in an AttributeError.
    assert "<p>Some nice html</p>" == job.description_rendered
