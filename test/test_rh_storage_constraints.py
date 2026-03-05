# SPDX-FileCopyrightText: PyPSA Contributors
#
# SPDX-License-Identifier: MIT

import pytest

import pypsa


@pytest.fixture(scope="module")
def _model():
    return pypsa.examples.model_energy()


@pytest.fixture(scope="class")
def rh_model(_model):
    m = _model.cluster.temporal.representative_hours(num_representative_hours=24)
    return m


class TestBuild:
    @pytest.fixture(scope="class")
    def rh_model_built(self, rh_model):
        rh_model.optimize.create_model()
        return rh_model

    @pytest.mark.parametrize(
        "constraint_name",
        ["StorageUnit-energy_balance", "Store-energy_balance"],
    )
    def test_storage_constraints_exist(self, request, constraint_name, rh_model_built):
        assert constraint_name in rh_model_built.model.constraints


class TestComponentDefs:
    @pytest.mark.parametrize(
        ("component", "attr"), [("StorageUnit", "p_nom"), ("Store", "e")]
    )
    @pytest.mark.parametrize("extendable", [[True], [False], [True, False]])
    def test_simultaneous_ext_and_non_ext_storage_constraints_exist(
        self,
        request,
        component,
        attr,
        extendable,
        rh_model,
    ):
        """Check that extendable / non-extendable `p_nom`/`e`, and a mixture of the two all create expected constraints"""
        template = rh_model.components[component].static.iloc[0]
        rh_model.remove(component, rh_model.components[component].static.index)
        for i, ext in enumerate(extendable):
            rh_model.add(component, f"s{i}", **{f"{attr}_extendable": ext, **template})
        rh_model.optimize.create_model()
        # TODO: check f"{component}-{attr}-inter-typical-period-{bound}"


class TestResults:
    @pytest.fixture(scope="class")
    def rh_model_opt(self, rh_model):
        rh_model.optimize()
        return rh_model

    def test_store_remains_within_limits(
        self,
        rh_model,
    ):
        """Check that Store `e` never exceeds defined limits."""
        storage_level = rh_model.components["Store"].dynamic["e"]
        max_storage_level = rh_model.components["Store"].static["e_nom_opt"]
        assert (storage_level.max() <= max_storage_level * 1.0001).all()

    def test_storageunit_remains_within_limits(self, rh_model):
        """Check that Storage Unit `state_of_charge` never exceeds defined limits."""
        storage_level = rh_model.components["StorageUnit"].dynamic["state_of_charge"]
        max_storage_level = (
            rh_model.components["StorageUnit"].static["p_nom_opt"]
            * rh_model.components["StorageUnit"].static["max_hours"]
        )
        assert (storage_level.max() <= max_storage_level * 1.0001).all()
