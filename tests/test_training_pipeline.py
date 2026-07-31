from annotation_schema import SentenceAnnotation
from training.train_gap_classifier import split_by_paper


def test_training_split_has_no_paper_leakage():
    records = [
        SentenceAnnotation(str(i), f"p{i//2}", "discussion", "", "sentence", "",
                           ["LIMITATION"], "test", "1", "reviewed")
        for i in range(10)
    ]
    train, validation, test = split_by_paper(records, 42)
    sets = [{record.paper_id for record in split}
            for split in (train, validation, test)]
    assert sets[0].isdisjoint(sets[1])
    assert sets[0].isdisjoint(sets[2])
    assert sets[1].isdisjoint(sets[2])
