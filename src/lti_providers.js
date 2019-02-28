const defaultLTIProvider = {
    supportsDeadline: false,
    supportsBonusPoints: false,
};

const blackboardProvider = Object.create(defaultLTIProvider);

const canvasProvider = Object.create(defaultLTIProvider, {
    supportsDeadline: {
        value: true,
    },
    supportsBonusPoints: {
        value: true,
    },
});

export default {
    Blackboard: blackboardProvider,
    Canvas: canvasProvider,
};
