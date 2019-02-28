const defaultLTIProvider = Object.create(null, {
    supportsDeadline: {
        value: false,
    },
    supportsBonusPoints: {
        value: false,
    },
    supportsStateManagement: {
        value: false,
    },
});

const blackboardProvider = Object.create(defaultLTIProvider);

const canvasProvider = Object.create(defaultLTIProvider, {
    supportsDeadline: {
        value: true,
    },
    supportsBonusPoints: {
        value: true,
    },
    supportsStateManagement: {
        value: true,
    },
});

export default {
    Blackboard: blackboardProvider,
    Canvas: canvasProvider,
};
