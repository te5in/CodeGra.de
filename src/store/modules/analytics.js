/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import { Workspace } from '@/models';
import * as types from '../mutation-types';

const getters = {
    getWorkspace: state =>
        (assignmentId, workspaceId) => state.workspaces[assignmentId][workspaceId],
    getAssignmentWorkspaces: state =>
        assignmentId => state.workspaces[assignmentId],
};

const loaders = {
    workspaces: {},
};

async function loadWorkspace(workspaceId) {
    const res = await axios.get(`/api/v1/analytics/${workspaceId}`);

    const sources = await Promise.all(
        res.data.data_sources.map(source =>
            axios
                .get(`/api/v1/analytics/${workspaceId}/data_sources/${source}`)
                .then(({ data }) => data),
        ),
    );

    res.data = Workspace.fromServerData(res.data, sources);
    return res;
}

const actions = {
    loadWorkspace({ commit, state }, { workspaceId, force }) {
        if (!force && Object.hasOwnProperty.call(state.workspaces, workspaceId)) {
            return state.workspaces[workspaceId];
        }

        if (!Object.hasOwnProperty.call(loaders.workspaces, workspaceId)) {
            loaders.workspaces[workspaceId] = loadWorkspace(workspaceId).then(
                workspace => {
                    delete loaders.workspaces[workspaceId];
                    commit(types.SET_WORKSPACE, { workspaceId, workspace });
                    return workspace;
                },
                err => {
                    delete loaders.workspaces[workspaceId];
                    throw err;
                },
            );
        }

        return loaders.workspaces[workspaceId];
    },

    clearAssignmentWorkspaces({ commit }, assignmentId) {
        commit(types.CLEAR_ASSIGNMENT_WORKSPACES, assignmentId);
    },
};

const mutations = {
    [types.SET_WORKSPACE](state, { workspaceId, workspace }) {
        const assignmentId = workspace.assignment_id;
        const workspaces = state.workspaces[assignmentId] || {};
        Vue.set(workspaces, workspaceId, workspace);
        Vue.set(state.workspaces, assignmentId, workspaces);
    },

    [types.CLEAR_ASSIGNMENT_WORKSPACES](state, assignmentId) {
        Vue.set(state.workspaces, assignmentId, {});
    },
};

export default {
    namespaced: true,
    state: {
        workspaces: {},
    },
    getters,
    actions,
    mutations,
};
