-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.PlayerConfig)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_6 = require(game.ReplicatedStorage.Shared.LVector3)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_8 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_9 = {
    ["Type"] = "HoldingNoteEffect_Adorn"
}
v_u_9.new = function(_, p10, p11, p12) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    local v13 = p10._lua_pool:depool(v_u_9.Type)
    if v13 == nil then
        local v14 = v_u_9:_new(p10, p11, p12)
        v14:cons()
        return v14;
    else
        v13:rebind(p10, p11, p12)
        v13:cons()
        return v13;
    end;
end;
v_u_9.prepool = function(_, p15) --[[ Name: prepool ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    p15._lua_pool:repool(v_u_9.Type, v_u_9:_new())
end;
v_u_9._new = function(_, p_u_16, p_u_17, p_u_18) --[[ Name: _new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_2, (copy 6): v_u_7, (copy 7): v_u_8, (copy 8): v_u_3, (copy 9): v_u_9 ]]
    local v19 = v_u_1:EffectBase()
    v19.rebind = function(_, p20, p21, p22) --[[ Name: rebind ]] --[[ Line: 33 ]]
        --[[ Upvalues: (ref 1): p_u_16, (ref 2): p_u_17, (ref 3): p_u_18 ]]
        p_u_16 = p20
        p_u_17 = p21
        p_u_18 = p22
    end;
    local v_u_23 = nil
    local v_u_24 = 0
    local v_u_25 = v_u_6.new(0, 0.4)
    local v_u_26 = v_u_6.new(1, 1)
    v19.cons = function(p27) --[[ Name: cons ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_23, (ref 3): p_u_16, (ref 4): v_u_5, (ref 5): p_u_17, (ref 6): p_u_18, (ref 7): v_u_4, (ref 8): v_u_2, (ref 9): v_u_7, (ref 10): v_u_8, (copy 11): v_u_25 ]]
        v_u_24 = 0
        v_u_23 = p_u_16._adorn_pool:depool(v_u_5.Type.Sphere)
        v_u_23.Radius = 1.5
        v_u_23.CFrame = CFrame.new(p_u_17)
        if p_u_18 == v_u_4.NoteResult_Okay then
            v_u_23.Color3 = v_u_2:color3(243, 237, 150)
        elseif p_u_18 == v_u_4.NoteResult_Great then
            v_u_23.Color3 = v_u_2:color3(100, 255, 100)
        else
            v_u_23.Color3 = v_u_2:color3(120, 255, 255)
        end;
        if p_u_16._player_settings_manager:get_key(v_u_7.Key.BrightnessSettings) == v_u_8.Normal then
            v_u_25.Y = 0.4
        else
            v_u_25.Y = 0.75
        end;
        p27:update_visual()
    end;
    local v_u_28 = v_u_6.new(0, 2)
    local v_u_29 = v_u_6.new(1, 3.4)
    v19.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_3, (copy 3): v_u_25, (copy 4): v_u_26, (ref 5): v_u_24, (copy 6): v_u_28, (copy 7): v_u_29 ]]
        v_u_23.Transparency = v_u_3:YForPointOf2PtLine(v_u_25, v_u_26, v_u_24)
        v_u_23.Radius = v_u_3:YForPointOf2PtLine(v_u_28, v_u_29, v_u_24) / 2
    end;
    v19.add_to_parent = function(_, _, _) end;
    v19.update = function(p30, p31, _) --[[ Name: update ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_3 ]]
        v_u_24 = v_u_24 + v_u_3:SecondsToTick(0.35) * p31
        p30:update_visual()
    end;
    v19.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 92 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24 >= 1;
    end;
    v19.do_remove = function(p32, _) --[[ Name: do_remove ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_23, (ref 3): v_u_9 ]]
        p_u_16._adorn_pool:repool(v_u_23)
        v_u_23 = nil
        p_u_16._lua_pool:repool(v_u_9.Type, p32)
    end;
    return v19;
end;
return v_u_9;
