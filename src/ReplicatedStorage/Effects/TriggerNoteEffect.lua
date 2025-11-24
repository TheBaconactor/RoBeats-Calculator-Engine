-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerConfig)
local v_u_6 = require(game.ReplicatedStorage.Effects.TriggerNoteEffect_Adorn)
local v_u_24 = {
    ["_new"] = function(_, p_u_7, p_u_8, p9, p_u_10) --[[ Name: _new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_2 ]]
        local v_u_11 = v_u_1:EffectBase()
        v_u_11.Type = "TriggerNoteEffect"
        if p_u_10 ~= true then
            p_u_10 = false
        end;
        v_u_11._effect_obj = nil
        v_u_11._anim_t = 0
        v_u_11._result = p9
        local v_u_12 = Vector3.new()
        local function f_update_visual(p13) --[[ Name: update_visual ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): v_u_11, (ref 2): v_u_3, (ref 3): v_u_4, (ref 4): p_u_10, (ref 5): v_u_12, (ref 6): v_u_2 ]]
            v_u_11._effect_obj.Body.Transparency = v_u_3:YForPointOf2PtLine(Vector2.new(0, 0.75), Vector2.new(1, 1), v_u_11._anim_t)
            local v14 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 2.25), Vector2.new(1, 4.25), v_u_11._anim_t)
            local v15
            if v_u_11._result == v_u_4.NoteResult_Okay then
                v15 = v14 * 0.25
            elseif v_u_11._result == v_u_4.NoteResult_Great then
                v15 = v14 * 0.5
            else
                v15 = v14 * 1
            end;
            if p_u_10 then
                v_u_12 = v_u_12 + Vector3.new(0, 0.01, 0)
                v_u_11._effect_obj:SetPrimaryPartCFrame(CFrame.new(v_u_12) * v_u_2:part_cframe_rotation(v_u_11._effect_obj.PrimaryPart))
            end;
            if p13 == true then
                v_u_11._effect_obj.Body.Size = Vector3.new(70, v15, v15)
            end;
        end;
        v_u_11.cons = function(p16, _) --[[ Name: cons ]] --[[ Line: 66 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_2, (ref 3): v_u_4, (ref 4): v_u_12, (copy 5): p_u_8, (copy 6): f_update_visual ]]
            p16._effect_obj = p_u_7._object_pool:depool(p16.Type)
            if p16._effect_obj == nil then
                p16._effect_obj = game.ReplicatedStorage.ElementProtos.TriggerHitEffectProto:Clone()
            end;
            p16._effect_obj.Name = v_u_2:gen_name(p16._effect_obj.Name)
            if p16._result == v_u_4.NoteResult_Okay then
                p16._effect_obj.PrimaryPart.BrickColor = BrickColor.new(243, 237, 150)
            elseif p16._result == v_u_4.NoteResult_Great then
                p16._effect_obj.PrimaryPart.BrickColor = BrickColor.new(0, 255, 0)
            else
                p16._effect_obj.PrimaryPart.BrickColor = BrickColor.new(0, 207, 256)
            end;
            v_u_12 = Vector3.new(p_u_8.X, p_u_7:get_game_environment_center().Y, p_u_8.Z)
            p16._effect_obj:SetPrimaryPartCFrame(CFrame.new(v_u_12) * v_u_2:part_cframe_rotation(p16._effect_obj.PrimaryPart))
            p16._anim_t = 0
            f_update_visual(true)
        end;
        v_u_11.add_to_parent = function(p17, p18, _) --[[ Name: add_to_parent ]] --[[ Line: 91 ]]
            p17._effect_obj.Parent = p18
        end;
        local v_u_19 = 0
        v_u_11.update = function(p20, p21, _) --[[ Name: update ]] --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (ref 3): v_u_19, (copy 4): f_update_visual ]]
            v_u_2:profilebegin("TriggerNoteEffect")
            p20._anim_t = p20._anim_t + v_u_3:SecondsToTick(0.25) * p21
            v_u_19 = v_u_19
            if v_u_19 > 2 then
                f_update_visual(true)
                v_u_19 = v_u_19 - 2
            else
                f_update_visual(false)
            end;
            v_u_2:profileend()
        end;
        v_u_11.should_remove = function(p22, _) --[[ Name: should_remove ]] --[[ Line: 112 ]]
            return p22._anim_t >= 1;
        end;
        v_u_11.do_remove = function(p23, _) --[[ Name: do_remove ]] --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_12, (ref 3): v_u_2, (copy 4): p_u_7 ]]
            if p_u_10 then
                v_u_12 = v_u_12 + Vector3.new(-999, -999, -999)
                p23._effect_obj:SetPrimaryPartCFrame(CFrame.new(v_u_12) * v_u_2:part_cframe_rotation(p23._effect_obj.PrimaryPart))
            end;
            p_u_7._object_pool:repool(p23.Type, p23._effect_obj)
            p23._effect_obj = nil
        end;
        v_u_11:cons(p_u_7)
        return v_u_11;
    end
}
v_u_24.new = function(_, p25, p26, p27, p28) --[[ Name: new ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (copy 3): v_u_24 ]]
    if v_u_5.GameEffectsUseAdorns == true then
        return v_u_6:new(p25, p26, p27, p28);
    else
        return v_u_24:_new(p25, p26, p27, p28);
    end;
end;
return v_u_24;
