-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_5 = require(game.ReplicatedStorage.Shared.LVector3)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_55 = {
    ["_new"] = function(_, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: _new ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_3 ]]
        local v17 = v_u_1:EffectBase()
        v17.rebind = function(_, p18, p19, p20, p21, p22, p23, p24, p25, p26, p27, p28) --[[ Name: rebind ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): p_u_6, (ref 2): p_u_7, (ref 3): p_u_8, (ref 4): p_u_9, (ref 5): p_u_10, (ref 6): p_u_11, (ref 7): p_u_12, (ref 8): p_u_13, (ref 9): p_u_14, (ref 10): p_u_15, (ref 11): p_u_16 ]]
            p_u_6 = p18
            p_u_7 = p19
            p_u_8 = p20
            p_u_9 = p21
            p_u_10 = p22
            p_u_11 = p23
            p_u_12 = p24
            p_u_13 = p25
            p_u_14 = p26
            p_u_15 = p27
            p_u_16 = p28
        end;
        local v_u_29 = nil
        local v_u_30 = 0
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = nil
        local v_u_41 = nil
        v17.cons = function(_) --[[ Name: cons ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_29, (ref 3): p_u_6, (ref 4): v_u_2, (ref 5): v_u_31, (ref 6): v_u_34, (ref 7): v_u_32, (ref 8): v_u_33, (ref 9): v_u_35, (ref 10): v_u_36, (ref 11): v_u_37, (ref 12): v_u_38, (ref 13): v_u_39, (ref 14): v_u_40, (ref 15): v_u_41, (ref 16): p_u_8, (ref 17): v_u_4 ]]
            v_u_30 = 0
            v_u_29 = p_u_6._object_pool:depool("EditorNoteResultPopupEffectDecal")
            if v_u_29 == nil then
                v_u_29 = game.ReplicatedStorage.ElementProtos.NoteResultPopupEffectDecal:Clone()
            end;
            v_u_29.Name = v_u_2:gen_name(v_u_29.Name)
            v_u_31 = v_u_29.Panel.SurfaceGui
            v_u_34 = v_u_31.Frame
            v_u_32 = v_u_34.UIScale
            v_u_33 = v_u_34.Size.X.Offset
            v_u_35 = v_u_34.ImageLabel
            v_u_36 = v_u_34.PointsDisplay
            v_u_37 = v_u_34.MultDisplay
            v_u_36.Text = ""
            v_u_37.Text = ""
            v_u_38 = v_u_34.ColorIconPrimary
            v_u_39 = v_u_34.ColorIconSecondary
            v_u_40 = v_u_34.ColorTextPrimary
            v_u_41 = v_u_34.ColorTextSecondary
            v_u_38.Visible = false
            v_u_39.Visible = false
            v_u_40.Text = ""
            v_u_41.Text = ""
            if p_u_8 == v_u_4.NoteResult_Miss then
                v_u_35.Image = v_u_2:get_hitword_miss_assetid()
                return;
            elseif p_u_8 == v_u_4.NoteResult_Okay then
                v_u_35.Image = v_u_2:get_hitword_okay_assetid()
                return;
            elseif p_u_8 == v_u_4.NoteResult_Great then
                v_u_35.Image = v_u_2:get_hitword_great_assetid()
            else
                v_u_35.Image = v_u_2:get_hitword_perfect_assetid()
            end;
        end;
        v17.set_frame_parent = function(_, p42) --[[ Name: set_frame_parent ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            v_u_34.Parent = p42
        end;
        local v_u_43 = Vector2.new(0, 0)
        v17.set_track_size = function(p44, p45) --[[ Name: set_track_size ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            v_u_43 = p45
            p44:update_visual()
        end;
        v17.get_anim_t = function(_) --[[ Name: get_anim_t ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30;
        end;
        v17.set_anim_t = function(_, p46) --[[ Name: set_anim_t ]] --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            v_u_30 = p46
        end;
        local v_u_47 = v_u_5.new(0, 0.65)
        local v_u_48 = v_u_5.new(1, 0)
        v17.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_33, (ref 3): v_u_32, (ref 4): v_u_34, (ref 5): p_u_7, (ref 6): v_u_3, (ref 7): v_u_30, (copy 8): v_u_47, (copy 9): v_u_48, (ref 10): v_u_2, (ref 11): v_u_35, (ref 12): v_u_36, (ref 13): v_u_37, (ref 14): v_u_40, (ref 15): v_u_41, (ref 16): v_u_38, (ref 17): v_u_39 ]]
            local v49 = v_u_43.X / v_u_33
            v_u_32.Scale = v49 * 2
            v_u_34.Position = UDim2.new(0, p_u_7.X, 0, p_u_7.Y + v_u_3:Lerp(0, v49 * 150, v_u_30))
            local v50 = v_u_2:tra((v_u_3:YForPointOf2PtLine(v_u_47, v_u_48, v_u_30)))
            v_u_35.ImageTransparency = v50
            v_u_36.TextTransparency = v50
            local v51 = v_u_2:tra(v_u_2:clamp(v_u_3:BezierPt2ForT(0, -1, 0.75, 0.25, 0.75, 0.25, 1, 0.75, 1 - v_u_30).Y, 0, 1))
            v_u_36.TextStrokeTransparency = v51
            v_u_37.TextTransparency = v50
            v_u_37.TextStrokeTransparency = v51
            v_u_40.TextTransparency = v50
            v_u_40.TextStrokeTransparency = v51
            v_u_41.TextTransparency = v50
            v_u_41.TextStrokeTransparency = v51
            v_u_38.ImageTransparency = v51
            v_u_39.ImageTransparency = v51
        end;
        v17.add_to_parent = function(_, _, _) end;
        v17.update = function(p52, p53, _) --[[ Name: update ]] --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_3 ]]
            v_u_30 = v_u_30 + v_u_3:SecondsToTick(0.55) * p53
            p52:update_visual()
        end;
        v17.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30 >= 1;
        end;
        v17.do_remove = function(p54, _) --[[ Name: do_remove ]] --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_31, (ref 3): p_u_6, (ref 4): v_u_29 ]]
            v_u_34.Parent = v_u_31
            p_u_6._object_pool:repool("EditorNoteResultPopupEffectDecal", v_u_29)
            p_u_6._lua_pool:repool("EditorNoteResultPopupEffectDecal", p54)
        end;
        return v17;
    end
}
local function _() --[[ Name: pool_str ]] --[[ Line: 12 ]]
    return "EditorNoteResultPopupEffectDecal";
end;
v_u_55.new = function(_, p56, p57, p58, p59, p60, p61, p62, p63, p64, p65, p66) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_55 ]]
    local v67 = p56._lua_pool:depool("EditorNoteResultPopupEffectDecal")
    if v67 == nil then
        local v68 = v_u_55:_new(p56, p57, p58, p59, p60, p61, p62, p63, p64, p65, p66)
        v68:cons()
        return v68;
    else
        v67:rebind(p56, p57, p58, p59, p60, p61, p62, p63, p64, p65, p66)
        v67:cons()
        return v67;
    end;
end;
v_u_55.prepool = function(_, p69) --[[ Name: prepool ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_55 ]]
    p69._lua_pool:repool("EditorNoteResultPopupEffectDecal", v_u_55:_new())
end;
return v_u_55;
