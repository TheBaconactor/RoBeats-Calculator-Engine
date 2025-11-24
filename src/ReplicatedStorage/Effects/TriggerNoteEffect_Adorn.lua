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
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_7 = {
    ["Type"] = "TriggerNoteEffect_Adorn"
}
v_u_7.new = function(_, p8, p9, p10) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    local v11 = p8._lua_pool:depool(v_u_7.Type)
    if v11 == nil then
        local v12 = v_u_7:_new(p8, p9, p10)
        v12:cons()
        return v12;
    else
        v11:rebind(p8, p9, p10)
        v11:cons()
        return v11;
    end;
end;
v_u_7.prepool = function(_, p13) --[[ Name: prepool ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    p13._lua_pool:repool(v_u_7.Type, v_u_7:_new())
end;
v_u_7._new = function(_, p_u_14, p_u_15, p_u_16) --[[ Name: _new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_2, (copy 6): v_u_3, (copy 7): v_u_7 ]]
    local v17 = v_u_1:EffectBase()
    v17.rebind = function(_, p18, p19, p20) --[[ Name: rebind ]] --[[ Line: 33 ]]
        --[[ Upvalues: (ref 1): p_u_14, (ref 2): p_u_15, (ref 3): p_u_16 ]]
        p_u_14 = p18
        p_u_15 = p19
        p_u_16 = p20
    end;
    local v_u_21 = nil
    local v_u_22 = 0
    local v_u_23 = v_u_6.new(0, 0.65)
    local v_u_24 = v_u_6.new(1, 1)
    v17.cons = function(p25, _) --[[ Name: cons ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21, (ref 3): p_u_14, (ref 4): v_u_5, (ref 5): p_u_15, (ref 6): p_u_16, (ref 7): v_u_4, (ref 8): v_u_2, (copy 9): v_u_23 ]]
        v_u_22 = 0
        v_u_21 = p_u_14._adorn_pool:depool(v_u_5.Type.Cylinder)
        v_u_21.Radius = 1.125
        v_u_21.Height = 70
        v_u_21.CFrame = CFrame.new(p_u_15) * v_u_5:cylinder_up_cframe()
        if p_u_16 == v_u_4.NoteResult_Okay then
            v_u_21.Color3 = v_u_2:color3(243, 237, 150)
        elseif p_u_16 == v_u_4.NoteResult_Great then
            v_u_21.Color3 = v_u_2:color3(100, 255, 100)
        else
            v_u_21.Color3 = v_u_2:color3(120, 255, 255)
        end;
        v_u_23.Y = 0.925
        p25:update_visual()
    end;
    local v_u_26 = v_u_6.new(0, 2.25)
    local v_u_27 = v_u_6.new(1, 3.5)
    v17.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_3, (copy 3): v_u_23, (copy 4): v_u_24, (ref 5): v_u_22, (copy 6): v_u_26, (copy 7): v_u_27, (ref 8): p_u_16, (ref 9): v_u_4 ]]
        v_u_21.Transparency = v_u_3:YForPointOf2PtLine(v_u_23, v_u_24, v_u_22)
        local v28 = v_u_3:YForPointOf2PtLine(v_u_26, v_u_27, v_u_22)
        local v29
        if p_u_16 == v_u_4.NoteResult_Okay then
            v29 = v28 * 0.25
        elseif p_u_16 == v_u_4.NoteResult_Great then
            v29 = v28 * 0.5
        else
            v29 = v28 * 1
        end;
        v_u_21.Radius = v29 * 0.5
    end;
    v17.add_to_parent = function(_, _, _) end;
    v17.update = function(p30, p31, _) --[[ Name: update ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_3 ]]
        v_u_22 = v_u_22 + v_u_3:SecondsToTick(0.25) * p31
        p30:update_visual()
    end;
    v17.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22 >= 1;
    end;
    v17.do_remove = function(p32, _) --[[ Name: do_remove ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_21, (ref 3): v_u_7 ]]
        p_u_14._adorn_pool:repool(v_u_21)
        v_u_21 = nil
        p_u_14._lua_pool:repool(v_u_7.Type, p32)
    end;
    return v17;
end;
return v_u_7;
