-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.Constants)
local v4 = {}
local v_u_5 = {
    {
        ["HeadText"] = "Error",
        ["SubText"] = "Could not load news.",
        ["ImageAssetId"] = nil
    }
}
v4.new = function(_, p_u_6) --[[ Name: new ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_3 ]]
    local v7 = {}
    local v_u_8 = v_u_5
    local v_u_9 = "?"
    local v_u_10 = false
    local v_u_11 = 0
    v7.start = function(_) --[[ Name: start ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_5 ]]
        p_u_6._evt:wait_on_event(v_u_1.EVT_News_ClientRequestNewsData, function(p_u_12) --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): p_u_6, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_5 ]]
            local function _() --[[ Name: send_news_data ]] --[[ Line: 35 ]]
                --[[ Upvalues: (ref 1): p_u_6, (ref 2): v_u_1, (copy 3): p_u_12, (ref 4): v_u_8, (ref 5): v_u_9 ]]
                p_u_6._evt:fire_event_to_client(v_u_1.EVT_News_ServerRequestNewsDataResponse, p_u_12, v_u_8, v_u_9)
            end;
            if v_u_10 == false then
                p_u_6._api:api_get_news(function(p13, p14) --[[ Line: 40 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_8, (ref 3): v_u_5, (ref 4): v_u_9, (ref 5): p_u_6, (ref 6): v_u_1, (copy 7): p_u_12 ]]
                    v_u_10 = true
                    if p13 == nil then
                        v_u_8 = v_u_5
                    else
                        v_u_8 = p13
                        v_u_9 = p14
                        p_u_6._evt:fire_event_to_client(v_u_1.EVT_News_ServerRequestNewsDataResponse, p_u_12, v_u_8, v_u_9)
                    end;
                end)
            else
                p_u_6._evt:fire_event_to_client(v_u_1.EVT_News_ServerRequestNewsDataResponse, p_u_12, v_u_8, v_u_9)
            end;
        end)
    end;
    v7.pull_news = function(_) --[[ Name: pull_news ]] --[[ Line: 57 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        v_u_10 = false
    end;
    v7.update = function(p15, p16) --[[ Name: update ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_11, (ref 3): v_u_3 ]]
        v_u_11 = v_u_11 + v_u_2:TimescaleToDeltaTime(p16)
        if v_u_11 > v_u_3.NEWS_REFRESH_TIME_SEC then
            v_u_11 = 0
            p15:pull_news()
        end;
    end;
    return v7;
end;
return v4;
