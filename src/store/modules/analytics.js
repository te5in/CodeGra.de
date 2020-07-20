/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import axios from 'axios';

import * as utils from '@/utils';
import * as types from '../mutation-types';

let Workspace = null;

const getters = {
    getWorkspace: state => workspaceId => state.workspaces[workspaceId],
    getAssignmentWorkspaces: state => assignmentId => {
        const workspaces = state.workspacesByAssignment[assignmentId];
        if (workspaces == null) {
            return {};
        }
        return utils.mapToObject([...state.workspacesByAssignment[assignmentId]], workspaceId => [
            workspaceId,
            state.workspaces[workspaceId],
        ]);
    },
};

const loaders = {
    workspaces: {},
    workspacesByAssignment: {},
};

async function loadWorkspace(workspaceId) {
    const promises = [axios.get(`/api/v1/analytics/${workspaceId}`)];
    if (Workspace == null) {
        promises.push(
            import('@/models/analytics').then(arg => {
                Workspace = arg.Workspace;
            }),
        );
    }
    const [res] = await Promise.all(promises);

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
            return Promise.resolve({ data: state.workspaces[workspaceId] });
        }

        if (!Object.hasOwnProperty.call(loaders.workspaces, workspaceId)) {
            loaders.workspaces[workspaceId] = loadWorkspace(workspaceId).then(
                workspace => {
                    delete loaders.workspaces[workspaceId];
                    commit(types.SET_WORKSPACE, { workspaceId, workspace: workspace.data });
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
        Vue.set(state.workspaces, workspaceId, workspace);

        const assignmentId = workspace.assignment_id;
        const assigWorkspaces = state.workspacesByAssignment[assignmentId] || new Set();
        assigWorkspaces.add(workspaceId);
        Vue.set(state.workspacesByAssignment, assignmentId, assigWorkspaces);
    },

    [types.CLEAR_ASSIGNMENT_WORKSPACES](state, assignmentId) {
        const ids = state.workspacesByAssignment[assignmentId];
        Vue.delete(state.workspacesByAssignment, assignmentId);

        if (ids != null) {
            ids.forEach(workspaceId => Vue.delete(state.workspaces, workspaceId));
        }
    },
};

export default {
    namespaced: true,
    state: {
        workspaces: {},
        workspacesByAssignment: {},
    },
    getters,
    actions,
    mutations,
};
