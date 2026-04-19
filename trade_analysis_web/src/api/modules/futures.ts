import axios from "@/api/axios";

export const getFutureDataApi = (params: { symbol: string; period: number }) => {
    return axios.get("/klines", {
        symbol: params.symbol,
        interval: params.period,
    });
};