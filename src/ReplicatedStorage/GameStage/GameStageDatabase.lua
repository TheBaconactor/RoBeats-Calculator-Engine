-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:05 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = {
    ["setup_game_stages"] = function(_) end
}
local v_u_4 = {
    "DefaultGameStageInfo",
    "EmptyDarkModeGameStageInfo",
    "TheMarkCustomServerStage",
    "SpringGameStage",
    "SDVBModernStage",
    "SDVBSpaceStationStage",
    "DeepSpaceStage",
    "HexagonSunsetStage",
    "NeonCityStage",
    "FNFCityStage",
    "SynthwaveShoresStage",
    "LonelyLittleStarStage",
    "HalloweenHauntsStage",
    "CakeStage",
    "ChristmasStage",
    "SoundSpaceLobbyStage",
    "PostApocalypticStage",
    "BeyondRealityCrystalStage",
    "BeachStage",
    "SummerCarnivalStage",
    "NoScopeStage",
    "AutumnStage",
    "InsightMountainStage",
    "SchoolCourtyardStage",
    "UnderwaterStage",
    "CastleStage",
    "CloudsStage",
    "Black17Stage",
    "SkyIslandsStage"
}
local v_u_5 = {}
v_u_3.new = function(_) --[[ Name: new ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_5 ]]
    local v6 = {
        ["get_default_stage_id"] = function(_) --[[ Name: get_default_stage_id ]] --[[ Line: 72 ]]
            return 1;
        end,
        ["get_default_dark_stage_id"] = function(_) --[[ Name: get_default_dark_stage_id ]] --[[ Line: 73 ]]
            return 2;
        end
    }
    local v_u_7 = v_u_1:new()
    local function f_load_requires() --[[ Name: load_requires ]] --[[ Line: 54 ]]
        --[[ Upvalues: (copy 1): v_u_7, (ref 2): v_u_2, (ref 3): v_u_4 ]]
        local function f_define_id_to_require(p8, p9) --[[ Name: define_id_to_require ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2 ]]
            local v10 = require(game.ReplicatedStorage.GameStage.Stages:FindFirstChild(p9))
            if v_u_7:contains(p8) then
                v_u_2:errf("already contains(%d)", p8)
            end;
            v_u_7:add(p8, v10:new())
        end;
        for v11 = 1, #v_u_4 do
            f_define_id_to_require(v11, v_u_4[v11])
        end;
    end;
    local function _() --[[ Name: cons ]] --[[ Line: 66 ]]
        --[[ Upvalues: (copy 1): f_load_requires ]]
        f_load_requires()
    end;
    v6.count = function(_) --[[ Name: count ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        return v_u_7:count();
    end;
    v6.contains_stageid = function(_, p12) --[[ Name: contains_stageid ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        return v_u_7:contains(p12);
    end;
    v6.get_default_game_stage_info = function(_) --[[ Name: get_default_game_stage_info ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        return v_u_7:get(1);
    end;
    v6.get_stage_info_for_id = function(p13, p14) --[[ Name: get_stage_info_for_id ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): v_u_7, (ref 2): v_u_2 ]]
        if v_u_7:contains(p14) then
            return v_u_7:get(p14);
        end;
        v_u_2:warnf("GameStageDatabase:get_stage_info_for_id(%s) does not exist", (tostring(p14)))
        return p13:get_default_game_stage_info();
    end;
    local v_u_15 = v_u_1:new()
    for _, v16 in pairs(v_u_5) do
        v_u_15:add_set(v16)
    end;
    v6.is_stage_new = function(_, p17) --[[ Name: is_stage_new ]] --[[ Line: 89 ]]
        --[[ Upvalues: (copy 1): v_u_15 ]]
        return v_u_15:contains(p17);
    end;
    f_load_requires()
    return v6;
end;
local v_u_18 = nil
v_u_3.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 98 ]]
    --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_3 ]]
    if v_u_18 == nil then
        v_u_18 = v_u_3:new()
    end;
    return v_u_18;
end;
return v_u_3;
