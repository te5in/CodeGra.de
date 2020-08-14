export interface GraderServerData {
    id: number;
    name: string;
    weight: number;
    done: boolean;
}

export interface Grader {
    userId: number;
    weight: number;
    done: boolean;
}

export type Graders = ReadonlyArray<Grader>;
