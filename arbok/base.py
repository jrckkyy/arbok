from warnings import warn

from sklearn.model_selection._search import BaseSearchCV
from sklearn.utils import check_X_y
from sklearn.utils.multiclass import unique_labels

from arbok import out


class Wrapper(BaseSearchCV):
    def __init__(self, estimator, preprocessor=None, refit=True, verbose=False, retry_on_error=True):

        # Call to super
        super(Wrapper, self).__init__(self.estimator)

        self.retry_on_error = retry_on_error
        self.estimator = estimator
        self.verbose = verbose
        self.refit = refit
        self.preprocessor = preprocessor

        # Redirect openml's call on self.best_estimator_.classes_, to self.classes_
        self.best_estimator_ = self
        self.classes__ = None

        # Define parameters
        self.cv_results_ = None
        self.best_index_ = None
        self.best_params_ = None
        self.best_score_ = None
        self.param_distributions = {}

    @property
    def classes_(self):
        return self.classes__

    def fit(self, X, y=None, groups=None, **fit_params):

        # Store the classes seen during fit
        self.classes__ = unique_labels(y)

        X_ = self.preprocessor.fit_transform(X) if self.preprocessor else X

        # Check that X and y have correct shape
        X, y = check_X_y(X_, y)

        try:
            aid = None
            if self.verbose:
                aid = out.start("Fitting")

            # Fit the wrapped estimator
            self._fit(X_, y, **fit_params)

            # Store results
            cv_results_, best_index_, best_params_, best_score_ = self._get_cv_results(self.estimator)
            self.cv_results_ = cv_results_
            self.best_index_ = best_index_
            self.best_params_ = best_params_
            self.best_score_ = best_score_

            if self.verbose:
                out.done("Fitting", aid)

            # Refit
            if self.refit:
                aid = out.start("Refitting")
                self._refit(X_, y)
                out.done("Refitting", aid)

        except ValueError as e:
            if self.retry_on_error:
                warn("Fitting failed. Attempting to fit again.")
                return self.fit(X_, y)
            raise e

        return self

    def get_params(self, deep=True):
        result = self.estimator.get_params(deep=deep)
        result['refit'] = self.refit
        result['verbose'] = self.verbose
        result['retry_on_error'] = self.retry_on_error
        result['preprocessor'] = self.preprocessor
        return result

    def set_params(self, **params):
        params = dict(self.get_params(), **params)
        self.refit = params.pop('refit')
        self.verbose = params.pop('verbose')
        self.retry_on_error = params.pop('retry_on_error')
        self.preprocessor = params.pop('preprocessor')
        self.estimator = self.estimator.set_params(**params)
        return self

    def predict(self, X):
        aid = None
        if self.verbose:
            aid = out.start("predict()")

        # Check is fit had been called
        self._check_is_fitted('predict')

        X_ = self.preprocessor.transform(X) if self.preprocessor else X
        predictions = self.estimator.predict(X_)
        if self.verbose:
            out.done("predict()", aid)
        return predictions

    def predict_proba(self, X):
        aid = None
        if self.verbose:
            aid = out.start("predict_proba()")

        # Check is fit had been called
        self._check_is_fitted('predict_proba')

        X_ = self.preprocessor.transform(X) if self.preprocessor else X

        try:
            predictions = self.estimator.predict_proba(X_)
        except (RuntimeError, AttributeError) as e:
            if self.verbose:
                out.fail("predict_proba()", aid)
            raise AttributeError()

        if self.verbose:
            out.done("predict_proba()", aid)

        return predictions

    def _get_cv_results(self, estimator):
        return NotImplementedError()

    def _fit(self, X, y, **fit_params):
        return NotImplementedError()

    def _refit(self, X, y):
        return NotImplementedError()
